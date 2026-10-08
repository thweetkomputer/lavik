/* Benchmark-only startup shim. Never install or preload this in production.
 * Sets the existing process digest seed before main, exactly once, so paired
 * fresh RESTORE populations have the same routing layout. No request-path
 * function is interposed. The launcher verifies the unchanged server binary,
 * resolves its private symbols and verifies the resulting seed in /proc. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <link.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
static int (*original_main)(int, char **, char **);
static uintptr_t executable_base;
static int base_callback(struct dl_phdr_info *info, size_t size, void *data) {
  (void)size; (void)data;
  if (!info->dlpi_name[0]) { executable_base = info->dlpi_addr; return 1; }
  return 0;
}
static int hex(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  _exit(121);
}
static int benchmark_main(int argc, char **argv, char **envp) {
  const char *seed = getenv("LAVIK_BENCH_FIXED_DIGEST_SEED");
  const char *offset = getenv("LAVIK_BENCH_DIGEST_FUNCTION_OFFSET");
  if (!seed || strlen(seed) != 32 || !offset) _exit(122);
  dl_iterate_phdr(base_callback, NULL);
  uintptr_t address = executable_base + strtoull(offset, NULL, 16);
  unsigned char *(*mutable_seed)(void) = (void *)address;
  unsigned char *target = mutable_seed();
  for (size_t i = 0; i < 16; ++i) target[i] = hex(seed[2*i])*16 + hex(seed[2*i+1]);
  static const char message[] = "BENCHMARK ONLY: fixed digest seed applied before main\n";
  if (write(STDERR_FILENO, message, sizeof(message)-1) < 0) _exit(123);
  return original_main(argc, argv, envp);
}
int __libc_start_main(int (*main_fn)(int, char **, char **), int argc,
                      char **argv, void (*init)(void), void (*fini)(void),
                      void (*rtld_fini)(void), void *stack_end) {
  typedef int (*start_fn)(int (*)(int,char **,char **), int, char **,
                          void (*)(void), void (*)(void), void (*)(void), void *);
  start_fn real_start = (start_fn)dlsym(RTLD_NEXT, "__libc_start_main");
  if (!real_start) _exit(124);
  original_main = main_fn;
  return real_start(benchmark_main, argc, argv, init, fini, rtld_fini, stack_end);
}
