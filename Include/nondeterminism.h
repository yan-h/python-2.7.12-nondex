#ifndef Py_NONDETERMINISM_H
#define Py_NONDETERMINISM_H

void NonDex_InitFull(Py_ssize_t seed);

void NonDex_Shuffle_Py_ssize_t(void *array, Py_ssize_t length);

#endif /* Py_NONDETERMINISM_H */
