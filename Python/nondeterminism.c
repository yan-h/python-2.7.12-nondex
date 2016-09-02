#include "Python.h"
#include <string.h>

enum mode {
    FULL, 
};

static enum mode NonDex_mode = FULL;
static unsigned int NonDex_seed = 1;

void NonDex_InitFull(Py_ssize_t seed)
{
    NonDex_mode = FULL;
    NonDex_seed = seed;
    srand(seed);
}

void NonDex_Shuffle_Py_ssize_t(Py_ssize_t *array, Py_ssize_t length)
{
    for (Py_ssize_t pos = length - 1; pos >= 0; pos--) {
        Py_ssize_t swap_pos = rand() % (pos + 1);
        Py_ssize_t temp = array[pos];
        array[pos] = array[swap_pos];
        array[swap_pos] = temp;
    }
}
