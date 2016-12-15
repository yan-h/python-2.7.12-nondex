#ifndef Py_NONDETERMINISM_H
#define Py_NONDETERMINISM_H

typedef enum NonDexMode {
    OFF,
    FULL,
    ONE
}NonDexMode;

NonDexMode NonDex_Mode(void);

void NonDex_InitFull(Py_ssize_t seed);
void NonDex_InitOne(Py_ssize_t init_seed);

void NonDex_Shuffle_Py_ssize_t(Py_ssize_t *array, Py_ssize_t length);
void NonDex_Shuffle_List(PyListObject *list);

#endif /* Py_NONDETERMINISM_H */
