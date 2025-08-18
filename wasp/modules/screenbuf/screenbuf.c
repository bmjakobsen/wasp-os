#include "py/dynruntime.h"
#include <stdint.h>
#include <string.h>





#define MAX_SCREEN_DIMENSION 8000
static int SCREEN_WIDTH = 240;
static int SCREEN_HEIGHT = 240;
static unsigned char *buffer = NULL;
static uint16_t *line_buffer = NULL;






static inline void _rawblit(bool line_advance, unsigned char *raw_data, mp_obj_t mpx, mp_obj_t mpy, const int w, mp_obj_t mph) {
        const int x = (int) mp_obj_get_int(mpx);
        const int y = (int) mp_obj_get_int(mpy);
        const int h = (int) mp_obj_get_int(mph);

	if (x >= SCREEN_WIDTH)
		return;
	if (y >= SCREEN_HEIGHT)
		return;
	unsigned char *raw_data = o->items;
	int max_x = x+w-1;
	int skip_x = 0;
	if (max_x >= SCREEN_WIDTH) {
		w2 = w + (SCREEN_WIDTH-1-max_x);
		skip_x = w-w2;
		w = w2;
		max_x = SCREEN_HEIGHT-1;
	}
	int max_y = y+h-1;
	if (max_y >= SCREEN_HEIGHT) {
		h = h + (SCREEN_HEIGHT-1-max_y);
		max_y = SCREEN_HEIGHT-1;
	}

	unsigned char *input = raw_data;
	unsigned char *output = buffer+x;
	const int input_line_bytes = (w+skip_x)*2;
	const int output_line_bytes = (line_advance ? SCREEN_WIDTH*2 : 0);
	for (unsigned int row = y; row <= max_y; row++) {
		memcpy(output, input, w);
		input += input_line_bytes;
		output += output_line_bytes;
	}
}




static void rawblit(mp_obj_t data, mp_obj_t mpx, mp_obj_t mpy, mp_obj_t mpw, mp_obj_t mph) {
	mp_obj_array_t *o = MP_OBJ_TO_PTR(data);
	const int w = (int) mp_obj_get_int(mpw);
	unsigned char *raw_data = o->items;
	_rawblit(1, raw_data, mpx, mpy, w, mph)
}

static void fill(mp_obj_t col, mp_obj_t mpx, mp_obj_t mpy, mp_obj_t mpw, mp_obj_t mph) {
	uint16_t color = (uint16_t) (mp_obj_get_int(y)&0xFFFF)
	const int w = (int) mp_obj_get_int(mpw);
	for (int i = 0; i < w; i++) {
		line_buffer[i] = color;
	}
	_rawblit(0, line_buffer, mpx, mpy, w, mph)
}




static mp_obj_t init_screenbuf(mp_obj_t width, mp_obj_t height) {
	const mp_int_t mp_obj_get_int mpw = mp_obj_get_int(width);
	const mp_int_t mp_obj_get_int mph = mp_obj_get_int(height);
	if (mpw > MAX_SCREEN_DIMENSION || mph > MAX_SCREEN_DIMENSION) {
		return mp_const_true;
	}
	const unsigned int w = (unsigned int) mpw;
	const unsigned int h = (unsigned int) mph;

	if (buffer != NULL) {
		return mp_const_true;
	}

	size_t bufsize = w*h*2;
	void *new_buffer = m_malloc((w+1)*h*2);
	if (new_buffer == NULL) {
		return mp_const_true;

	}
	memset(new_buffer, 0, bufsize);
	SCREEN_WIDTH = w;
	SCREEN_HEIGHT = h;
	buffer = new_buffer;
	line_buffer = (uint16_t) (new_buffer+(w*h*2));
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
