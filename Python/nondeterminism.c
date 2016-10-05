#include "Python.h"
#include <string.h>
#include "mt64.h"

enum NonDexMode {
    FULL, 
    ONE
};

static enum NonDexMode mode = FULL;
static unsigned int seed = 1;

void NonDex_InitFull(Py_ssize_t init_seed)
{
    mode = FULL;
    seed = init_seed;
    init_genrand64(init_seed);
}

void NonDex_InitOne(Py_ssize_t init_seed)
{
    mode = ONE;
    seed = init_seed;
    init_genrand64(init_seed);
}

void NonDex_Shuffle_Py_ssize_t(Py_ssize_t *array, Py_ssize_t length)
{
    if (mode == ONE) {
        init_genrand64(seed);
    }
    
    for (Py_ssize_t pos = length - 1; pos >= 0; pos--) {
        Py_ssize_t swap_pos = genrand64_int64() % (pos + 1);
        Py_ssize_t temp = array[pos];
        array[pos] = array[swap_pos];
        array[swap_pos] = temp;
    }
}
