// Task-local random-key RESP benchmark. Each write independently chooses add
// or pop with equal probability. One outstanding command per connection.
#include <arpa/inet.h>
#include <netinet/tcp.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>
#include <fcntl.h>
#include <algorithm>
#include <barrier>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
using Clock=std::chrono::steady_clock;
std::string resp(const std::vector<std::string>& args) {std::string s="*"+std::to_string(args.size())+"\r\n";for(auto&a:args)s+="$"+std::to_string(a.size())+"\r\n"+a+"\r\n";return s;}
struct Value {char tag;std::string text;std::vector<Value> children;};
bool parse(const std::string&s,size_t&pos,Value&v){if(pos>=s.size())return false;auto end=s.find("\r\n",pos);if(end==std::string::npos)return false;v.tag=s[pos];auto head=s.substr(pos+1,end-pos-1);pos=end+2;
 if(v.tag=='$'){auto n=std::stol(head);if(n<0)throw std::runtime_error("nil reply");if(pos+n+2>s.size())return false;v.text=s.substr(pos,n);pos+=n+2;if(s.substr(pos-2,2)!="\r\n")throw std::runtime_error("bulk terminator");}
 else if(v.tag=='*'){auto n=std::stol(head);if(n<0||n>8)throw std::runtime_error("bad array length");for(int i=0;i<n;++i){Value child;if(!parse(s,pos,child))return false;v.children.push_back(std::move(child));}}
 else if(v.tag==':'||v.tag=='+')v.text=head;else throw std::runtime_error("server/error reply "+head);return true;}
uint64_t random64(uint64_t&s){uint64_t z=(s+=0x9e3779b97f4a7c15ULL);z=(z^(z>>30))*0xbf58476d1ce4e5b9ULL;z=(z^(z>>27))*0x94d049bb133111ebULL;return z^(z>>31);}
struct Conn {int fd,id,phase=0,key=0,expected_pos=0;size_t sent=0;bool done=false;uint64_t rng,seq=0;std::string input,wire;Clock::time_point start;};
struct Stats {std::vector<uint64_t> latency[2];std::vector<uint64_t> counts[2];uint64_t min_count=UINT64_MAX,max_count=0;};
std::string seed(int pos,int bytes){std::ostringstream s;s<<std::setfill('0')<<std::setw(8)<<pos;return s.str()+std::string(bytes-8,'x');}
int main(int argc,char**argv){try {
 if(argc!=10)throw std::runtime_error("host port operation connections keys entries field_bytes seconds seed");
 std::string host=argv[1],op=argv[3];int port=std::stoi(argv[2]),conns=std::stoi(argv[4]),keys=std::stoi(argv[5]),entries=std::stoi(argv[6]),bytes=std::stoi(argv[7]),seconds=std::stoi(argv[8]);uint64_t rndseed=std::stoull(argv[9]);
 if(conns<1||keys<1||entries<1||bytes<32||seconds<1)throw std::runtime_error("bad args");
 bool list=op=="LPUSH_RPOP"||op=="RPUSH_LPOP",zadd=op.rfind("ZADD_",0)==0,mixed=list||zadd;
 std::vector<std::string> names=op=="LPUSH_RPOP"?std::vector<std::string>{"LPUSH","RPOP"}:op=="RPUSH_LPOP"?std::vector<std::string>{"RPUSH","LPOP"}:zadd?std::vector<std::string>{"ZADD",op=="ZADD_HEAD_ZPOPMAX"?"ZPOPMAX":"ZPOPMIN"}:std::vector<std::string>{op};
 std::atomic<uint64_t> score_ticket{0};
 auto prepare=[&](Conn&c){c.key=random64(c.rng)%keys;c.phase=mixed?random64(c.rng)%2:0;std::string key="complex_"+std::to_string(c.key+1);
  if(mixed&&c.phase==1)c.wire=resp({names[1],key});
  else if(list||zadd||op=="LSET") {uint64_t ticket=++c.seq*uint64_t(conns)+c.id;std::string member="bench-"+std::to_string(ticket);member+=std::string(bytes-member.size(),'y');
   if(list)c.wire=resp({names[0],key,member});
   else if(zadd){auto ordinal=score_ticket.fetch_add(1,std::memory_order_relaxed);double score=op=="ZADD_HEAD_ZPOPMAX"?-1.0-double(ordinal):op=="ZADD_TAIL_ZPOPMIN"?entries+1.0+double(ordinal):double(random64(c.rng)%uint64_t(entries*1000000ULL))/1000000.0;std::ostringstream s;s<<std::setprecision(17)<<score;c.wire=resp({"ZADD",key,"NX",s.str(),member});}
   else {int pos=(entries-1)*(random64(c.rng)%8)/7;c.wire=resp({op,key,std::to_string(pos),member});}
  }else {int pos=(entries-1)*(random64(c.rng)%8)/7;c.expected_pos=pos;if(op=="LINDEX")c.wire=resp({op,key,std::to_string(pos)});else if(op=="ZRANK"||op=="ZSCORE")c.wire=resp({op,key,seed(pos,bytes)});else throw std::runtime_error("unknown operation");}
  c.sent=0;c.start=Clock::now();};
 std::vector<Conn> cs;cs.reserve(conns);
 for(int i=0;i<conns;++i){int fd=socket(AF_INET,SOCK_STREAM,0);if(fd<0)throw std::runtime_error("socket");sockaddr_in addr{};addr.sin_family=AF_INET;addr.sin_port=htons(port);inet_pton(AF_INET,host.c_str(),&addr.sin_addr);if(connect(fd,(sockaddr*)&addr,sizeof(addr)))throw std::runtime_error("connect: "+std::string(strerror(errno)));int one=1;setsockopt(fd,IPPROTO_TCP,TCP_NODELAY,&one,sizeof(one));fcntl(fd,F_SETFL,fcntl(fd,F_GETFL)|O_NONBLOCK);Conn c{fd,i};c.rng=rndseed^(uint64_t(i+1)*0xd1342543de82ef95ULL);cs.push_back(std::move(c));}
 int nt=std::min(16,conns);std::barrier sync(nt+1);std::vector<Stats> stats(nt);std::vector<std::string> errors(nt);std::atomic<bool> abort=false;Clock::time_point begin,deadline;std::vector<std::thread> threads;
 for(auto&s:stats)for(int i=0;i<(mixed?2:1);++i){s.counts[i].resize(keys);s.latency[i].reserve(200000);}
 for(int t=0;t<nt;++t)threads.emplace_back([&,t]{sync.arrive_and_wait();try {
 std::vector<Conn*> owned;for(int i=t;i<conns;i+=nt){prepare(cs[i]);owned.push_back(&cs[i]);}std::vector<pollfd> polls(owned.size());size_t active=owned.size();
 while(active&&!abort){for(size_t j=0;j<owned.size();++j){auto&c=*owned[j];polls[j]={c.done?-1:c.fd,short(c.sent<c.wire.size()?POLLOUT:POLLIN),0};}int ready=poll(polls.data(),polls.size(),1000);if(ready<0){if(errno==EINTR)continue;throw std::runtime_error("poll");}if(Clock::now()>deadline+std::chrono::seconds(120))throw std::runtime_error("drain timeout");
 for(size_t j=0;j<owned.size();++j){auto&c=*owned[j];if(c.done)continue;auto re=polls[j].revents;if(re&(POLLERR|POLLHUP|POLLNVAL))throw std::runtime_error("socket closed");if(re&POLLOUT){auto n=send(c.fd,c.wire.data()+c.sent,c.wire.size()-c.sent,MSG_NOSIGNAL);if(n>0)c.sent+=n;else if(n<0&&errno!=EAGAIN&&errno!=EWOULDBLOCK&&errno!=EINTR)throw std::runtime_error("send");}
 if(!(re&POLLIN))continue;char buf[4096];auto n=recv(c.fd,buf,sizeof(buf),0);if(n<=0){if(n<0&&(errno==EAGAIN||errno==EWOULDBLOCK||errno==EINTR))continue;throw std::runtime_error("recv");}c.input.append(buf,n);Value v;size_t pos=0;if(!parse(c.input,pos,v))continue;if(pos!=c.input.size())throw std::runtime_error("unsolicited reply");c.input.clear();auto now=Clock::now();
 if(list&&c.phase==0){if(v.tag!=':')throw std::runtime_error("push not integer");uint64_t count=std::stoull(v.text);if(count<uint64_t(entries/2)||count>uint64_t(entries*2))throw std::runtime_error("list population guard");stats[t].min_count=std::min(stats[t].min_count,count);stats[t].max_count=std::max(stats[t].max_count,count);}
 else if(list){if(v.tag!='$'||v.text.size()!=size_t(bytes))throw std::runtime_error("empty/wrong list pop");}
 else if(zadd&&c.phase==0){if(v.tag!=':'||v.text!="1")throw std::runtime_error("ZADD did not insert new member");}
 else if(zadd){if(v.tag!='*'||v.children.size()!=2||v.children[0].tag!='$'||v.children[0].text.size()!=size_t(bytes)||v.children[1].tag!='$')throw std::runtime_error("empty/wrong ZPOP reply");}
 else if(op=="LINDEX"){if(v.tag!='$'||v.text.size()!=size_t(bytes))throw std::runtime_error("LINDEX invalid");}
 else if(op=="LSET"){if(v.tag!='+'||v.text!="OK")throw std::runtime_error("LSET invalid");}
 else if(op=="ZRANK"){auto rank=std::stoll(v.text);if(v.tag!=':'||rank!=c.expected_pos)throw std::runtime_error("ZRANK invalid");}
 else if(v.tag!='$'||std::stod(v.text)!=c.expected_pos)throw std::runtime_error("score invalid");
 stats[t].latency[c.phase].push_back(std::chrono::duration_cast<std::chrono::nanoseconds>(now-c.start).count());++stats[t].counts[c.phase][c.key];
 if(now>=deadline){c.done=true;--active;}else prepare(c);
 }} }catch(const std::exception&e){errors[t]=e.what();abort=true;}});
 begin=Clock::now();deadline=begin+std::chrono::seconds(seconds);sync.arrive_and_wait();for(auto&t:threads)t.join();double elapsed=std::chrono::duration<double>(Clock::now()-begin).count();for(auto&c:cs)close(c.fd);for(auto&e:errors)if(!e.empty())throw std::runtime_error(e);
 std::vector<uint64_t> all,by[2],counts[2];for(auto&c:counts)c.resize(keys);uint64_t min_count=UINT64_MAX,max_count=0;
 for(auto&s:stats){min_count=std::min(min_count,s.min_count);max_count=std::max(max_count,s.max_count);for(int i=0;i<(mixed?2:1);++i){by[i].insert(by[i].end(),s.latency[i].begin(),s.latency[i].end());for(int k=0;k<keys;++k)counts[i][k]+=s.counts[i][k];}}
 for(int i=0;i<(mixed?2:1);++i)all.insert(all.end(),by[i].begin(),by[i].end());
 auto report=[&](std::vector<uint64_t>&v){if(v.empty())throw std::runtime_error("empty samples");std::sort(v.begin(),v.end());auto p=[&](double q){return v[size_t(std::ceil(q*v.size()))-1]/1e6;};std::cout<<"{\"count\":"<<v.size()<<",\"qps\":"<<v.size()/elapsed<<",\"p50_ms\":"<<p(.5)<<",\"p99_ms\":"<<p(.99)<<",\"p999_ms\":"<<p(.999)<<"}";};
 std::cout<<std::setprecision(12)<<"{\"operation\":\""<<op<<"\",\"seconds\":"<<seconds<<",\"elapsed_seconds\":"<<elapsed<<",\"connections\":"<<conns<<",\"keys\":"<<keys<<",\"entries\":"<<entries<<",\"field_bytes\":"<<bytes<<",\"seed\":"<<rndseed<<",\"pipeline\":1,\"threads\":"<<nt<<",\"errors\":0,\"totals\":";report(all);std::cout<<",\"commands\":{";for(size_t i=0;i<names.size();++i){if(i)std::cout<<",";std::cout<<"\""<<names[i]<<"\":";report(by[i]);}std::cout<<"},\"key_counts\":{";
 for(int k=0;k<keys;++k){if(k)std::cout<<",";std::cout<<"\"complex_"<<k+1<<"\":{\"first\":"<<counts[0][k]<<",\"second\":"<<counts[1][k]<<",\"net\":"<<(mixed?int64_t(counts[0][k])-int64_t(counts[1][k]):0)<<"}";}
 std::cout<<"},\"observed_push_min\":"<<(min_count==UINT64_MAX?0:min_count)<<",\"observed_push_max\":"<<max_count<<"}\n";
 }catch(const std::exception&e){std::cerr<<"ERROR "<<e.what()<<"\n";return 1;}}
