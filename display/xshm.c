#include <Python.h>
#include <sys/ipc.h>
#include <sys/shm.h>
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/extensions/XShm.h>

#define offscreen 0

typedef struct {
  XImage* m_shm_image;
  XShmSegmentInfo m_shminfo;
  int m_width, m_height;
} XImage_Shm;

typedef struct {
  PyObject_HEAD
  Display* dpy;
  int default_scr;
  Window root, win;
  int width, height;
  XVisualInfo visual_info;
  GC gc, gc_and, gc_or;
  XImage_Shm planes[1];
  Pixmap backpixmap;
  int shmmode;
  int selectinput;
} DisplayObject;

typedef struct {
  PyObject_HEAD
  DisplayObject* dpy;
  int width, height;
  Pixmap mask;
  Pixmap handle;
} XPixmapObject;


#define DisplayObject_Check(v)	((v)->ob_type == &Display_Type)
staticforward PyTypeObject Display_Type;
staticforward PyTypeObject XPixmap_Type;


static void pixmap_dealloc(XPixmapObject* pm)
{
  if (pm->dpy->dpy)
    {
      if (pm->mask != (Pixmap) -1)
        XFreePixmap(pm->dpy->dpy, pm->mask);
      XFreePixmap(pm->dpy->dpy, pm->handle);
    }
  Py_DECREF(pm->dpy);
  PyObject_Del(pm);
}

static XPixmapObject* new_pixmap(DisplayObject* self, int w, int h, int withmask)
{
  XPixmapObject* pm = PyObject_New(XPixmapObject, &XPixmap_Type);
  if (pm != NULL)
    {
      Py_INCREF(self);
      pm->dpy = self;
      pm->width = w;
      pm->height = h;
      pm->handle = XCreatePixmap(self->dpy, self->win, w, h,
                                 self->visual_info.depth);
      if (withmask)
        pm->mask = XCreatePixmap(self->dpy, self->win, w, h,
                                 self->visual_info.depth);
      else
        pm->mask = (Pixmap) -1;
    }
  return pm;
}


static void flush(DisplayObject* self)
{
  XSync(self->dpy, False);
}

static int create_shm_image(DisplayObject* self, XImage_Shm* img,
                            int width, int height)
{
  int image_size = 4*width*height;
	
  if (XShmQueryExtension(self->dpy) == False)
    // does we have the extension at all?
    return 0;
	
  img->m_shm_image = XShmCreateImage(
		self->dpy,
		self->visual_info.visual,
		self->visual_info.depth,
		ZPixmap,
		NULL,
		&img->m_shminfo,
		width,
		height);
  if (img->m_shm_image == NULL)
    return 0;
  img->m_width = width;
  img->m_height = height;

  // Create shared memory segment:
  img->m_shminfo.shmid = shmget(IPC_PRIVATE, image_size, IPC_CREAT|0777);
  if (img->m_shminfo.shmid < 0)
    return 0;
	
  // Get memory address to segment:
  img->m_shminfo.shmaddr = (char *) shmat(img->m_shminfo.shmid, 0, 0);

  // Tell XServer that it may only read from it and attach to display:
  img->m_shminfo.readOnly = True;
  XShmAttach (self->dpy, &img->m_shminfo);

  // Fill the XImage struct:
  img->m_shm_image->data = img->m_shminfo.shmaddr;
  return 1;
}

static PyObject* new_display(PyObject* dummy, PyObject* args)
{
  DisplayObject* self;
  XSetWindowAttributes attr;
  int width, height, use_shm=1;
  if (!PyArg_ParseTuple(args, "ii|i", &width, &height, &use_shm))
    return NULL;

  self = PyObject_New(DisplayObject, &Display_Type);
  if (self == NULL)
    return NULL;

  self->dpy = XOpenDisplay(NULL);
  if (self->dpy == NULL) goto err;
  self->default_scr = DefaultScreen(self->dpy);
  self->root = RootWindow(self->dpy, self->default_scr);
  self->width = width;
  self->height = height;

  if (!XMatchVisualInfo(self->dpy, self->default_scr,
                        DefaultDepth(self->dpy,self->default_scr), TrueColor,
                        &self->visual_info)) goto err2;

  self->backpixmap = XCreatePixmap(self->dpy, self->root,
                                   width, height, self->visual_info.depth);
  if (self->backpixmap == (Pixmap) -1) goto err2;

  /* set window attributes */
  memset(&attr, 0, sizeof(attr));
  attr.override_redirect = False;
  attr.background_pixel = BlackPixel(self->dpy, self->default_scr);
  attr.backing_store = NotUseful;

  /* Create the window */
  self->win = XCreateWindow(
		self->dpy,
		self->root,
		0,
		0,
		width,
		height,
		0,
		CopyFromParent,
		CopyFromParent,
		self->visual_info.visual,
		CWOverrideRedirect | CWBackPixel | CWBackingStore,
		&attr);
  if (self->win == (Window) -1) goto err2;

  XMapRaised(self->dpy, self->win);
  
  self->shmmode = use_shm &&
    create_shm_image(self, &self->planes[0], width, height);
  
  self->gc = XCreateGC(self->dpy, self->win, 0, 0);
  if (!self->shmmode)
    {
      self->gc_and = XCreateGC(self->dpy, self->win, 0, 0);
      self->gc_or = XCreateGC(self->dpy, self->win, 0, 0);
      XSetForeground(self->dpy, self->gc, attr.background_pixel);
      XSetFunction(self->dpy, self->gc_and, GXand);
      XSetFunction(self->dpy, self->gc_or, GXor);
    }
  
  self->selectinput = 0;

  flush(self);
  return (PyObject*) self;

 err2:
  XCloseDisplay(self->dpy);
 err:
  Py_DECREF(self);
  PyErr_SetString(PyExc_IOError, "cannot open X11 display");
  return NULL;
}

static void display_close(DisplayObject* self)
{
  if (self->dpy)
    {
      XCloseDisplay(self->dpy);
      self->dpy = NULL;
    }
}

static void display_dealloc(DisplayObject* self)
{
  display_close(self);
  PyObject_Del(self);
}

static PyObject* display_close1(DisplayObject* self, PyObject* args)
{
  display_close(self);
  Py_INCREF(Py_None);
  return Py_None;
}

static int checkopen(DisplayObject* self)
{
  if (self->dpy)
    return 1;
  PyErr_SetString(PyExc_IOError, "X11 connexion already closed");
  return 0;
}

static unsigned char* get_dpy_data(DisplayObject* self)
{
  unsigned char* result;
  if (!checkopen(self))
    return NULL;
  result = (unsigned char*)(self->planes[0].m_shminfo.shmaddr);
  if (!result)
    PyErr_SetString(PyExc_IOError, "X11 SHM failed");
  return result;
}

static PyObject* display_flip1(DisplayObject* self, PyObject* args)
{
  if (!checkopen(self))
    return NULL;

  if (self->shmmode)
    {
      XShmPutImage(self->dpy, self->win, self->gc,
                   self->planes[0].m_shm_image,
                   0, 0, 0, 0,
                   self->planes[0].m_width,
                   self->planes[0].m_height,
                   False);
    }
  else
    {
      XCopyArea(self->dpy, self->backpixmap, self->win, self->gc,
                0, 0, self->width, self->height, 0, 0);
    }
  flush(self);
  Py_INCREF(Py_None);
  return Py_None;
}

static PyObject* display_clear1(DisplayObject* self, PyObject* args)
{
  if (self->shmmode)
    {
      unsigned char* data = get_dpy_data(self);
      if (data == NULL)
        return NULL;
      memset(data, 0,
	     ( self->planes[0].m_shm_image->bits_per_pixel/8
	       *self->width*self->height ) );
    }
  else
    {
      if (!checkopen(self))
        return NULL;
      XFillRectangle(self->dpy, self->backpixmap, self->gc,
                     0, 0, self->width, self->height);
    }
  Py_INCREF(Py_None);
  return Py_None;
}

static void pack_pixel(unsigned char *data, int r, int g, int b,
		       int depth, int bytes_per_pixel)
{
  unsigned short pixel = 0;
  switch( depth )
    {
      /* No True color below 15 bits per pixel */
    case 15:
      pixel = ((r<<7) & 0x7c00) | ((g<<2) & 0x03e0) | ((b>>3) & 0x001f);
      data[0] = (pixel) & 0xff;
      data[1] = (pixel>>8) & 0xff;
      break;
    case 16:
      /* assumes 5,6,5 model. */
      pixel = ((r<<8) & 0xf800) | ((g<<3) & 0x07e0) | ((b>>3) & 0x001f);
      data[0] = (pixel) & 0xff;
      data[1] = (pixel>>8) & 0xff;
      break;
    case 24:
      if( bytes_per_pixel == 3 )
	{
	  data[0] = b;
	  data[1] = g;
	  data[2] = r;
	  break;
	}
      /* else it's on 32 bits. Drop into depth of 32. */
    case 32:
      *((long *)data) = (r<<16) | (g<<8) | b;
      break;
    }
}

static PyObject* display_pixmap1(DisplayObject* self, PyObject* args)
{
  int w,h;
  int length;
  XImage* image;
  long extent;
  unsigned char* data = NULL;
  unsigned char* maskdata = NULL;
  unsigned char* input = NULL;
  int scanline, bitmap_pad;
  XPixmapObject* pm;
  long keycol = -1;
  unsigned int bytes_per_pixel = (self->visual_info.depth+7)/8;

  if (!checkopen(self))
    return NULL;
  if (!PyArg_ParseTuple(args, "ii|s#l", &w, &h, &input, &length, &keycol))
    return NULL;
 
  if (self->shmmode)
    {
      int x, y;
      unsigned char *dst;
      int size;
      long packed_keycol = keycol;
      PyObject* result;
      PyObject* str;

      bytes_per_pixel = self->planes[0].m_shm_image->bits_per_pixel/8;
      size = bytes_per_pixel*w*h;

      if (input == NULL )
        {
          Py_INCREF(Py_None);
          return Py_None;
        }
      if( 3*w*h != length )
	{
	  PyErr_SetString(PyExc_TypeError, "bad string length");
	  return NULL;
	}
      /* Create a new string and fill it with the correctly packed image */
      str = PyString_FromStringAndSize(NULL, size);
      if (!str)
        return NULL;
      if (keycol >= 0)
	switch( self->visual_info.depth )
	  {
	  case 15:
	    packed_keycol = (1 << 10) | (1 << 5) | 1;
	    break;
	  case 16:
	    packed_keycol = (1 << 11) | (1 << 5) | 1;
	    break;
	  default:
	    packed_keycol = keycol;
	    break;
	  }
      result = Py_BuildValue("iiOl", w, h, str, packed_keycol);
      Py_DECREF(str);  /* one ref left in 'result' */
      if (!result)
        return NULL;
      dst = (unsigned char*) PyString_AS_STRING(str);
      memset(dst,0,size);

      for( y=0; y<h; y++ )
	for( x=0; x<w; x++, input+=3, dst += bytes_per_pixel )
	  {
	    unsigned int r = input[0];
	    unsigned int g = input[1];
	    unsigned int b = input[2];
	    if( ((r<<16)|(g<<8)|b) == keycol )
	      for( b=0; b<bytes_per_pixel; b++ )
		dst[b] = ((unsigned char *)&packed_keycol)[b];
	    else
	      pack_pixel(dst, r, g, b, self->visual_info.depth, bytes_per_pixel);
	  }
      return result;
    }

  pm = new_pixmap(self, w, h, keycol>=0);
  if (pm == NULL)
    return NULL;

  if (input == NULL)
    return (PyObject*) pm;   /* uninitialized pixmap */
  
  extent = w*h;
  if (3*extent != length)
    {
      PyErr_SetString(PyExc_TypeError, "bad string length");
      goto err;
    }

  bitmap_pad = self->visual_info.depth >= 24 ? 32 : 16;
  scanline = ((w+bitmap_pad-1) & ~(bitmap_pad-1)) / 8;
  /*while (scanline&3) scanline++;*/
  data = malloc(self->visual_info.depth*scanline*h);
  if (data == NULL)
    {
      PyErr_NoMemory();
      goto err;
    }
  memset(data, 0, self->visual_info.depth*scanline*h);
  maskdata = malloc(self->visual_info.depth*scanline*h);
  if (maskdata == NULL)
    {
      PyErr_NoMemory();
      goto err;
    }
  memset(maskdata, 0, self->visual_info.depth*scanline*h);

  {
    int key_r = keycol>>16;
    unsigned char key_g = keycol>>8;
    unsigned char key_b = keycol>>0;
    unsigned char* target = data;
    unsigned char* masktarget = maskdata;
    int plane, color;

    unsigned int p_size[3];
    switch( self->visual_info.depth )
      {
      case 15:
	p_size[0] = p_size[1] = p_size[2] = 5;
	break;
      case 16:
	p_size[0] = p_size[2] = 5;
	p_size[1] = 6;
	break;
      case 24:
      case 32:
	p_size[0] = p_size[1] = p_size[2] = 8;
	break;
      }

    for (color=0; color<3; color++)
      for (plane=128; plane>=(1<<(8-p_size[color])); plane/=2)
        {
          unsigned char* src = input;
          int x, y;
          for (y=0; y<h; y++, target+=scanline, masktarget+=scanline)
            for (x=0; x<w; x++, src+=3)
              {
                if (src[0] == key_r && src[1] == key_g && src[2] == key_b)
                  {
                    /* transparent */
                    masktarget[x/8] |= (1<<(x&7));
                  }
                else
                  if (src[color] & plane)
                    target[x/8] |= (1<<(x&7));
              }
        }
  }

  if (keycol < 0)
    free(maskdata);
  else
    {
      image = XCreateImage(self->dpy, self->visual_info.visual,
			   self->visual_info.depth, XYPixmap, 0,
                           maskdata, w, h,
			   bitmap_pad, scanline);
      if (image == NULL || image == (XImage*) -1)
        {
          PyErr_SetString(PyExc_IOError, "XCreateImage failed (2)");
          goto err;
        }
      image->byte_order = LSBFirst;
      image->bitmap_bit_order = LSBFirst;
      maskdata = NULL;
      XPutImage(self->dpy, pm->mask, self->gc, image, 0, 0, 0, 0, w, h);
      XDestroyImage(image);
    }
  
  image = XCreateImage(self->dpy, self->visual_info.visual,
		       self->visual_info.depth, XYPixmap, 0,
                       data, w, h,
                       bitmap_pad, scanline);
  if (image == NULL || image == (XImage*) -1)
    {
      PyErr_SetString(PyExc_IOError, "XCreateImage failed");
      goto err;
    }
  image->byte_order = LSBFirst;
  image->bitmap_bit_order = LSBFirst;
  data = NULL;
  XPutImage(self->dpy, pm->handle, self->gc, image, 0, 0, 0, 0, w, h);
  XDestroyImage(image);

  return (PyObject*) pm;

 err:
  free(maskdata);
  free(data);
  Py_DECREF(pm);
  return NULL;
}

static PyObject* display_putppm1(DisplayObject* self, PyObject* args)
{
  if (self->shmmode)
    {
      int x,y,w,h,scanline;
      int clipx=0, clipy=0, clipw=65536, cliph=65536;
      unsigned char* src;
      int length;
      long keycol;
      unsigned int bytes_per_pixel = self->planes[0].m_shm_image->bits_per_pixel/8;
      unsigned char* data = get_dpy_data(self);
      if (!PyArg_ParseTuple(args, "ii(iis#l)|(iiii)",
                            &x, &y, &w, &h, &src, &length, &keycol,
                            &clipx, &clipy, &clipw, &cliph) || !data)
        return NULL;
  
      scanline = bytes_per_pixel*w;
      if (scanline*h != length)
        {
          PyErr_SetString(PyExc_TypeError, "bad string length");
          return NULL;
        }
      x -= clipx;
      y -= clipy;
      clipx += x;
      clipy += y;
      clipw += clipx;
      cliph += clipy;
      if (clipx<0) clipx=0;
      if (clipy<0) clipy=0;
      if (clipw>self->width) clipw=self->width;
      if (cliph>self->height) cliph=self->height;
      if (x<clipx) { src+=(clipx-x)*bytes_per_pixel; w+=x-clipx; x=clipx; }
      if (y<clipy) { src+=(clipy-y)*scanline; h+=y-clipy; y=clipy; }
      if (x+w > clipw) w = clipw-x;
      if (y+h > cliph) h = cliph-y;
      data += bytes_per_pixel*(x+y*self->width);
      while (h>0)
        {
          int i;
	  int b;
          unsigned char* src0 = src;
	  unsigned char* data0 = data;
          if (keycol < 0)
            for (i=0; i<w; i++)
	      for (b=0; b<bytes_per_pixel; b++)
		*data++ = *src++;
          else
	    {
	      unsigned char *keycol_bytes = (unsigned char *)&keycol;
	      for (i=0; i<w; i++)
		{
		  int transparent = 1;
		  for( b=0; b<bytes_per_pixel; b++ )
		    transparent = transparent && (keycol_bytes[b] == src[b]);

		  if (!transparent)
		    for( b=0; b<bytes_per_pixel; b++ )
		      *data++ = *src++;
		  else
		    {
		      data += bytes_per_pixel;
		      src += bytes_per_pixel;
		    }
		}
	    }
          src = src0 + scanline;
          data = data0 + bytes_per_pixel*self->width;
          h--;
        }
    }
  else
    {
      int x,y, x1=0,y1=0,w1=-1,h1=-1;
      XPixmapObject* pm;

      if (!checkopen(self))
        return NULL;
      if (!PyArg_ParseTuple(args, "iiO!|(iiii)", &x, &y, &XPixmap_Type, &pm,
                            &x1, &y1, &w1, &h1))
        return NULL;
  
      if (w1 < 0)
        w1 = pm->width;
      if (h1 < 0)
        h1 = pm->height;

      if (pm->mask == (Pixmap) -1)
        {
          XCopyArea(self->dpy, pm->handle, self->backpixmap, self->gc,
                    x1, y1, w1, h1, x, y);
        }
      else
        {
          XCopyArea(self->dpy, pm->mask, self->backpixmap, self->gc_and,
                    x1, y1, w1, h1, x, y);
          XCopyArea(self->dpy, pm->handle, self->backpixmap, self->gc_or,
                    x1, y1, w1, h1, x, y);
        }
    }
  Py_INCREF(Py_None);
  return Py_None;
}

static PyObject* display_getppm1(DisplayObject* self, PyObject* args)
{
  if (self->shmmode)
    {
      int x,y,w,h,scanline;
      int clipx=0, clipy=0, clipw=self->width, cliph=self->height;
      unsigned char* dst;
      int length;
      PyObject* ignored;
      PyObject* result;
      PyObject* str;
      unsigned int bytes_per_pixel = self->planes[0].m_shm_image->bits_per_pixel/8;
      unsigned char* data = get_dpy_data(self);
      if (!PyArg_ParseTuple(args, "(iiii)|O", &x, &y, &w, &h,
                            &ignored) || !data)
        return NULL;

      scanline = bytes_per_pixel*w;
      length = scanline*h;
      str = PyString_FromStringAndSize(NULL, length);
      if (!str)
        return NULL;
      result = Py_BuildValue("iiOl", w, h, str, -1);
      Py_DECREF(str);  /* one ref left in 'result' */
      if (!result)
        return NULL;
      dst = (unsigned char*) PyString_AS_STRING(str);

      if (x<clipx) { dst+=(clipx-x)*bytes_per_pixel; w+=x-clipx; x=clipx; }
      if (y<clipy) { dst+=(clipy-y)*scanline; h+=y-clipy; y=clipy; }
      if (x+w > clipw) w = clipw-x;
      if (y+h > cliph) h = cliph-y;
      data += bytes_per_pixel*(x+y*self->width);
      while (h>0)
        {
          int i;
	  int b;
          unsigned char* dst0 = dst;
	  unsigned char* data0 = data;
          for (i=0; i<w; i++)
            {
	      for( b=0; b<bytes_per_pixel; b++ )
		*dst++ = *data++;
            }
          dst = dst0 + scanline;
          data = data0 + bytes_per_pixel*self->width;
          h--;
        }
      return result;
    }
  else
    {
      int x,y,w,h;
      XPixmapObject* pm = NULL;
      if (!checkopen(self))
        return NULL;
      if (!PyArg_ParseTuple(args, "(iiii)|O!", &x, &y, &w, &h,
                            &XPixmap_Type, &pm))
        return NULL;

      if (pm == NULL)
        {
          pm = new_pixmap(self, w, h, 0);
          if (pm == NULL)
            return NULL;
        }
      else
        Py_INCREF(pm);
      XCopyArea(self->dpy, self->backpixmap, pm->handle, self->gc,
                x, y, w, h, 0, 0);
      return (PyObject*) pm;
    }
}

#define INPUT_EVENTS_LOOP(e, mask)                              \
  if (!(self->selectinput & (mask)))                            \
    {                                                           \
      self->selectinput |= (mask);                              \
      XSelectInput(self->dpy, self->win, self->selectinput);    \
    }                                                           \
  while (XCheckMaskEvent(self->dpy, (mask), &(e)))

static PyObject* display_keyevents1(DisplayObject* self, PyObject* args)
{
  PyObject* result = PyList_New(0);
  if (result)
    {
      XEvent e;
      INPUT_EVENTS_LOOP(e, KeyPressMask|KeyReleaseMask)
	{
	  KeySym sym = XLookupKeysym(&e.xkey,0);
	  PyObject* v = Py_BuildValue("ii", sym, e.type);
	  int err = !v || PyList_Append(result, v) < 0;
	  Py_XDECREF(v);
	  if (err)
	    {
	      Py_DECREF(result);
	      return NULL;
	    }
	}
    }
  return result;
}

static PyObject* display_mouseevents1(DisplayObject* self, PyObject* args)
{
  PyObject* result = PyList_New(0);
  if (result)
    {
      XEvent e;
      INPUT_EVENTS_LOOP(e, ButtonPressMask)
	{
	  PyObject* v = Py_BuildValue("ii", e.xbutton.x, e.xbutton.y);
	  int err = !v || PyList_Append(result, v) < 0;
	  Py_XDECREF(v);
	  if (err)
	    {
	      Py_DECREF(result);
	      return NULL;
	    }
	}
    }
  return result;
}

static PyObject* display_pointermotion1(DisplayObject* self, PyObject* args)
{
  XEvent e;
  PyObject* result;
  Py_INCREF(Py_None);
  result = Py_None;
  
  INPUT_EVENTS_LOOP(e, PointerMotionMask)
    {
      Py_DECREF(result);
      result = Py_BuildValue("ii", e.xmotion.x, e.xmotion.y);
      if (!result)
        return NULL;
    }
  return result;
}

static PyObject* display_fd1(DisplayObject* self, PyObject *args)
{
  return PyInt_FromLong(ConnectionNumber(self->dpy));
}

static PyObject* display_shmmode(DisplayObject* self, PyObject *args)
{
  return PyInt_FromLong(self->shmmode);
}

static PyMethodDef display_methods[] = {
  {"close",    (PyCFunction)display_close1,    METH_VARARGS,  NULL},
  {"flip",     (PyCFunction)display_flip1,     METH_VARARGS,  NULL},
  {"clear",    (PyCFunction)display_clear1,    METH_VARARGS,  NULL},
  {"pixmap",   (PyCFunction)display_pixmap1,   METH_VARARGS,  NULL},
  {"putppm",   (PyCFunction)display_putppm1,   METH_VARARGS,  NULL},
  {"getppm",   (PyCFunction)display_getppm1,   METH_VARARGS,  NULL},
  {"keyevents",(PyCFunction)display_keyevents1,METH_VARARGS,  NULL},
  {"mouseevents",(PyCFunction)display_mouseevents1,METH_VARARGS,NULL},
  {"pointermotion",(PyCFunction)display_pointermotion1,METH_VARARGS,NULL},
  {"fd",       (PyCFunction)display_fd1,       METH_VARARGS,  NULL},
  {"shmmode",  (PyCFunction)display_shmmode,   METH_VARARGS,  NULL},
  {NULL,		NULL}		/* sentinel */
};

static PyObject* display_getattr(DisplayObject* self, char* name)
{
  return Py_FindMethod(display_methods, (PyObject*)self, name);
}


statichere PyTypeObject Display_Type = {
	PyObject_HEAD_INIT(NULL)
	0,			/*ob_size*/
	"Display",		/*tp_name*/
	sizeof(DisplayObject),	/*tp_basicsize*/
	0,			/*tp_itemsize*/
	/* methods */
	(destructor)display_dealloc, /*tp_dealloc*/
	0,			/*tp_print*/
	(getattrfunc)display_getattr, /*tp_getattr*/
	0,			/*tp_setattr*/
	0,			/*tp_compare*/
	0,			/*tp_repr*/
	0,			/*tp_as_number*/
	0,			/*tp_as_sequence*/
	0,			/*tp_as_mapping*/
	0,			/*tp_hash*/
	0,			/*tp_call*/
};

statichere PyTypeObject XPixmap_Type = {
	PyObject_HEAD_INIT(NULL)
	0,			/*ob_size*/
	"Pixmap",		/*tp_name*/
	sizeof(XPixmapObject),	/*tp_basicsize*/
	0,			/*tp_itemsize*/
	/* methods */
	(destructor)pixmap_dealloc, /*tp_dealloc*/
	0,			/*tp_print*/
	0,			/*tp_getattr*/
	0,			/*tp_setattr*/
	0,			/*tp_compare*/
	0,			/*tp_repr*/
	0,			/*tp_as_number*/
	0,			/*tp_as_sequence*/
	0,			/*tp_as_mapping*/
	0,			/*tp_hash*/
	0,			/*tp_call*/
};


static PyMethodDef ShmMethods[] = {
           {"Display",  new_display,  METH_VARARGS},
           {NULL,       NULL}         /* Sentinel */
       };

void initxshm(void)
{
  Display_Type.ob_type = &PyType_Type;
  XPixmap_Type.ob_type = &PyType_Type;
  Py_InitModule("xshm", ShmMethods);
}
