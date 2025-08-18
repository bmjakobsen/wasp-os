#include "py/dynruntime.h"
#include <stdint.h>
#include <string.h>


#define MAX_SCREEN_DIMENSION 8000
static unsigned int SCREEN_WIDTH = 240;
static unsigned int SCREEN_HEIGHT = 240;
static uint16_t *buffer = NULL;






static void rawblit(mp_obj_t scb, mp_obj_t)




static mp_obj_t init_screenbuf(mp_obj_t width, mp_obj_t height) {
	const mp_obj_get_int mpw = mp_obj_get_int(width);
	const mp_obj_get_int mph = mp_obj_get_int(height);
	if (mpw > MAX_SCREEN_DIMENSION || mph > MAX_SCREEN_DIMENSION) {
		return mp_const_true;
	}
	const unsigned int w = (unsigned int) mpw;
	const unsigned int h = (unsigned int) mph;

	if (buffer != NULL) {
		return mp_const_true;
	}

	size_t bufsize = w*h*2;
	void *new_buffer = m_malloc(w*h*2);
	if (new_buffer == NULL) {
		return mp_const_true;

	}
	memset(new_buffer, 0, bufsize);
	SCREEN_WIDTH = w;
	SCREEN_HEIGHT = h;
	buffer = new_buffer;
	mp_obj_array_t *o = m_new_obj(mp_obj_array_t);
	mp_obj_memoryview_init(o, BYTEARRAY_TYPECODE, 0, bufsize, buffer);
	return MP_OBJ_FROM_PTR(o)
}




mp_obj_t mpy_init(mp_obj_fun_bc_t *self, size_t n_args, size_t n_kw, mp_obj_t *args) {
    // This must be first, it sets up the globals dict and other things
    MP_DYNRUNTIME_INIT_ENTRY

    // Make the function available in the module's namespace
    mp_store_global(MP_QSTR_factorial, MP_OBJ_FROM_PTR(&factorial_obj));

    // This must be last, it restores the globals dict
    MP_DYNRUNTIME_INIT_EXIT
}
