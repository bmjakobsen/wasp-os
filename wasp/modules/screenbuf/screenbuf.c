#include "py/runtime.h"
#include <stdint.h>
#include <string.h>
#include "py/obj.h"
#include "py/objarray.h"
#include "py/binary.h"





#define MAX_SCREEN_DIMENSION 8000
static int SCREEN_WIDTH = 240;
static int SCREEN_HEIGHT = 240;
static unsigned char *buffer = NULL;
static uint16_t *line_buffer = NULL;






static inline void _rawblit(bool line_advance, unsigned char *raw_data, mp_obj_t mpx, mp_obj_t mpy, int w, mp_obj_t mph) {
        int x = (int) mp_obj_get_int(mpx);
        int y = (int) mp_obj_get_int(mpy);
        int h = (int) mp_obj_get_int(mph);

	if (x >= SCREEN_WIDTH)
		return;
	if (y >= SCREEN_HEIGHT)
		return;
	int max_x = x+w-1;
	int skip_x = 0;
	if (max_x >= SCREEN_WIDTH) {
		int w2 = w + (SCREEN_WIDTH-1-max_x);
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




static mp_obj_t rawblit(size_t n_args, const mp_obj_t *args) {
	mp_obj_t data = args[0];
	mp_obj_t mpx = args[1];
	mp_obj_t mpy = args[2];
	mp_obj_t mpw = args[3];
	mp_obj_t mph = args[4];

	mp_obj_array_t *o = MP_OBJ_TO_PTR(data);
	int w = (int) mp_obj_get_int(mpw);
	unsigned char *raw_data = o->items;
	_rawblit(1, raw_data, mpx, mpy, w, mph);
	return mp_const_none;
}

static mp_obj_t fill(size_t n_args, const mp_obj_t *args) {
	mp_obj_t col = args[0];
	mp_obj_t mpx = args[1];
	mp_obj_t mpy = args[2];
	mp_obj_t mpw = args[3];
	mp_obj_t mph = args[4];

	uint16_t color = (uint16_t) (mp_obj_get_int(col)&0xFFFF);
	int w = (int) mp_obj_get_int(mpw);
	for (int i = 0; i < w; i++) {
		line_buffer[i] = color;
	}
	_rawblit(0, (unsigned char *) line_buffer, mpx, mpy, w, mph);
	return mp_const_none;
}




static mp_obj_t init_screenbuf(mp_obj_t width, mp_obj_t height) {
	const mp_int_t mpw = mp_obj_get_int(width);
	const mp_int_t mph = mp_obj_get_int(height);
	if (mpw > MAX_SCREEN_DIMENSION || mph > MAX_SCREEN_DIMENSION) {
		return mp_const_none;
	}
	const unsigned int w = (unsigned int) mpw;
	const unsigned int h = (unsigned int) mph;

	if (buffer != NULL) {
		return mp_const_none;
	}

	size_t bufsize = w*h*2;
	void *new_buffer = m_malloc((w+1)*h*2);
	if (new_buffer == NULL) {
		return mp_const_none;
	}
	memset(new_buffer, 0, bufsize);
	SCREEN_WIDTH = w;
	SCREEN_HEIGHT = h;
	buffer = new_buffer;
	line_buffer = (uint16_t*) (new_buffer+(w*h*2));
	mp_obj_array_t *o = m_new_obj(mp_obj_array_t);
	mp_obj_memoryview_init(o, BYTEARRAY_TYPECODE, 0, bufsize, buffer);
	return MP_OBJ_FROM_PTR(o);
}

STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(rawblit_obj, 5, 5, rawblit);
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(fill_obj, 5, 5, fill);
STATIC MP_DEFINE_CONST_FUN_OBJ_2(init_screenbuf_obj, init_screenbuf);



STATIC const mp_rom_map_elem_t screenbuf_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_cexample) },
    { MP_ROM_QSTR(MP_QSTR_init_screenbuf), MP_ROM_PTR(&init_screenbuf_obj) },
    { MP_ROM_QSTR(MP_QSTR_rawblit), MP_ROM_PTR(&rawblit_obj) },
    { MP_ROM_QSTR(MP_QSTR_fill), MP_ROM_PTR(&fill_obj) },
};
STATIC MP_DEFINE_CONST_DICT(screenbuf_module_globals, screenbuf_module_globals_table);



const mp_obj_module_t screenbuf_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&screenbuf_module_globals,
};
MP_REGISTER_MODULE(MP_QSTR_screenbuf, screenbuf_user_cmodule, 1);

