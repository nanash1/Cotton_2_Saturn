/*
 ============================================================================
 Name        : ss_cotton_lz00.c
 Author      : nanashi
 Description : ss_cotton_lz00 compression Python extension
 ============================================================================
 */

#define PY_SSIZE_T_CLEAN
#include <Python.h>

struct match {
		Py_ssize_t pos;
		Py_ssize_t match_len;
};

/**
 * @brief	finds matches between look ahead buffer and search buffer
 * @param	labuff			Pointer to look ahead buffer
 * @param	max_len			Size of the look ahead buffer
 * @param	sbuff			Pointer to search buffer
 * @param	sbuff_start		Starting position in the search buffer
 * @param	sbuff_stop		Stopping position in the search buffer
 * @param	check_repeats	If >0 the function checks if matches repeat
 * @return	Length of the match
 */
static Py_ssize_t find_match(
		const char* labuff,
		Py_ssize_t max_len,
		const char* sbuff,
		Py_ssize_t sbuff_start,
		Py_ssize_t sbuff_stop,
		int check_repeats)
{
	Py_ssize_t match_len = sbuff_stop - sbuff_start;
	Py_ssize_t match;

	/* check if there is a match */
	for (Py_ssize_t i = 0; i < match_len; i++){
		if (labuff[i] != sbuff[sbuff_start+i]) return 0;
	}
	match = match_len;
	Py_ssize_t j = sbuff_start;

	/* check if the found match repeats in the look ahead buffer */
	if (check_repeats){
		while (match < max_len){
			if (labuff[match] == sbuff[j]){
				match++;
				j++;
			} else {
				break;
			}

			if (j - sbuff_start > match_len - 1) j = sbuff_start;
		}
	}

	return match;
}

/**
 * @brief	Finds the best match between look ahead buffer and search buffer
 * @param	self			Python self object
 * @param	args			Python arguments
 * @return	Tuple of (indicator string, match position, match length)
 */
static PyObject* ss_cotton_lz00_find_best_match(PyObject *self, PyObject *args)
{
	/* get arguments from python api */
	const char* labuff;
	Py_ssize_t max_len;
	const char* sbuff;
	Py_ssize_t sbuff_len;
    if (!PyArg_ParseTuple(args, "y#y#", &labuff, &max_len, &sbuff, &sbuff_len))
        return NULL;

    /* initialize variables */
    struct match ret;
    ret.match_len = 0;
    ret.pos = 0;
    Py_ssize_t pos = 0;
    Py_ssize_t max_match_len = 0;
    Py_ssize_t match_len;
    int check_repeats;

    /* go through the search buffer and look for matches */
    while (pos < sbuff_len){
    	for (int i = 0; i < pos+1; i++){
    		check_repeats = (pos == i);
    		match_len = find_match(labuff, max_len, sbuff,
    				sbuff_len-1-pos, sbuff_len-pos+i, check_repeats);

    		if (match_len > max_match_len){
    			ret.pos = pos+1;
    			ret.match_len = match_len,
				max_match_len = match_len;
    		} else if (match_len == 0){
    			break;
    		}
    	}
    	pos++;
    }

    return Py_BuildValue("sii", "seq", ret.pos, ret.match_len);
}

static PyMethodDef ss_cotton_lz00_methods[] = {
    {"find_best_match",  ss_cotton_lz00_find_best_match, METH_VARARGS,
     "Finds the best match of the search buffer data in the look ahead buffer."},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

static struct PyModuleDef ss_cotton_lz00_module = {
    PyModuleDef_HEAD_INIT,
    "ss_cotton_lz00",   /* name of module */
    "Acceleration module for ss cotton 2 LZ00 compression", /* module documentation, may be NULL */
    -1,       /* size of per-interpreter state of the module,
                 or -1 if the module keeps state in global variables. */
	ss_cotton_lz00_methods
};

PyMODINIT_FUNC
PyInit_ss_cotton_lz00(void)
{
    return PyModule_Create(&ss_cotton_lz00_module);
}
