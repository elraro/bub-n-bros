#include <Python.h>
#include <sys/ipc.h>
#include <sys/shm.h>
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/extensions/XShm.h>

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
  XImage_Shm plane;
  Pixmap backpixmap;
  int shmmode;
  int selectinput;
  PyObject* keyevents;
  PyObject* mouseevents;
  PyObject* motionevent;
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
    /* does we have the extension at all? */
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

  /* Create shared memory segment: */
  img->m_shminfo.shmid = shmget(IPC_PRIVATE, image_size, IPC_CREAT|0777);
  if (img->m_shminfo.shmid < 0)
    return 0;
	
  /* Get memory address to segment: */
  img->m_shminfo.shmaddr = (char *) shmat(img->m_shminfo.shmid, 0, 0);

  /* Tell XServer that it may only read from it and attach to display: */
  img->m_shminfo.readOnly = True;
  XShmAttach (self->dpy, &img->m_shminfo);

  /* Fill the XImage struct: */
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
    create_shm_image(self, &self->plane, width, height);
  
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
  self->keyevents = NULL;
  self->mouseevents = NULL;
  self->motionevent = NULL;

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
  Py_XDECREF(self->keyevents);
  Py_XDECREF(self->mouseevents);
  Py_XDECREF(self->motionevent);
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
  result = (unsigned char*)(self->plane.m_shminfo.shmaddr);
  if (!result)
    PyErr_SetString(PyExc_IOError, "X11 SHM failed");
  return result;
}

static PyObject* display_clear1(DisplayObject* self, PyObject* args)
{
  if (self->shmmode)
    {
      unsigned char* data = get_dpy_data(self);
      if (data == NULL)
        return NULL;
      memset(data, 0,
	     ( self->plane.m_shm_image->bits_per_pixel/8
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

inline void pack_pixel(unsigned char *data, int r, int g, int b,
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

typedef unsigned char code_t;

static PyObject* display_pixmap1(DisplayObject* self, PyObject* args)
{
  int w,h;
  unsigned char* input = NULL;
  int length;
  long keycol = -1;

  if (!checkopen(self))
    return NULL;
  if (!PyArg_ParseTuple(args, "ii|s#l", &w, &h, &input, &length, &keycol))
    return NULL;

  if (self->shmmode)
    {
      int x, y;
      int bytes_per_pixel = self->plane.m_shm_image->bits_per_pixel/8;
      char* sp;
      PyObject* result = NULL;
      PyObject* lines = NULL;
      code_t* buffer = NULL;
      int totalbufsize, linebufsize;
      PyObject* str;

      if (input == NULL)
        {
          Py_INCREF(Py_None);
          return Py_None;
        }
      if (3*w*h != length)
	{
	  PyErr_SetString(PyExc_ValueError, "bad string length");
          goto finally;
	}

      lines = PyList_New(h);
      if (lines == NULL)
        goto finally;

      linebufsize = 10+5*w;  /* enough for any packed single line */
      buffer = malloc(linebufsize);
      if (buffer == NULL) {
        PyErr_NoMemory();
        goto finally;
      }

      /* Convert the image to our internal format.
         See display_putppm1() for a description of the format.
      */

      totalbufsize = h * sizeof(int);
      for (y=0; y<h; y++)
        {
          code_t state = 0;
          code_t* pcounter = NULL;
          code_t* p = buffer;

          for (x=0; x<w; x++)
            {
              unsigned int r = input[0];
              unsigned int g = input[1];
              unsigned int b = input[2];
              input += 3;
              if (((r<<16)|(g<<8)|b) == keycol)
                {
                  if (state != 2 || *pcounter > 255-bytes_per_pixel)
                    {
                      *p++ = state = 2;
                      pcounter = p++;
                      *pcounter = 0;
                    }
                  *pcounter += bytes_per_pixel;
                }
              else
                {
                  if (state != 1 || *pcounter > 255-bytes_per_pixel)
                    {
                      /* align the following block to a 'long' boundary */
                      while ((((long) p) & 3) != 2)
                        *p++ = 0;
                      *p++ = state = 1;
                      pcounter = p++;
                      *pcounter = 0;
                    }
                  *pcounter += bytes_per_pixel;
                  pack_pixel(p, r, g, b, self->visual_info.depth, bytes_per_pixel);
                  p += bytes_per_pixel;
                }
            }
          /* align again */
          while ((((long) p) & 3) != 0)
            *p++ = 0;

          x = p-buffer;
          if (!(0 <= x && x <= linebufsize))
            Py_FatalError("Internal buffer overflow in display.pixmap");
          
          totalbufsize += x;
          str = PyString_FromStringAndSize(buffer, x);
          if (str == NULL)
            goto finally;
          PyList_SET_ITEM(lines, y, str);
        }

      /* fprintf(stderr, "%dx%d:  %d bytes instead of %d\n", w, h,
             totalbufsize, bytes_per_pixel*w*h); */
      
      /* compact all the lines into a single string buffer */
      str = PyString_FromStringAndSize(NULL, totalbufsize);
      if (str == NULL)
        goto finally;

      sp = PyString_AS_STRING(str);
      totalbufsize = h * sizeof(int);
      for (y=0; y<h; y++)
        {
          PyObject* src = PyList_GET_ITEM(lines, y);
          ((int*)sp)[y] = totalbufsize;
          memcpy(sp + totalbufsize, PyString_AS_STRING(src),
                                    PyString_GET_SIZE(src));
          totalbufsize += PyString_GET_SIZE(src);
        }
      
      result = Py_BuildValue("iiOi", w, h, str, -1);
      Py_DECREF(str);

    finally:
      free(buffer);
      Py_XDECREF(lines);
      return result;
    }
  else
    {
      XImage* image;
      long extent;
      unsigned char* data = NULL;
      unsigned char* maskdata = NULL;
      int scanline, bitmap_pad;
      XPixmapObject* pm;

      pm = new_pixmap(self, w, h, keycol>=0);
      if (pm == NULL)
        return NULL;

      if (input == NULL)
        return (PyObject*) pm;   /* uninitialized pixmap */
  
      extent = w*h;
      if (3*extent != length)
        {
          PyErr_SetString(PyExc_ValueError, "bad string length");
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
}

static PyObject* display_putppm1(DisplayObject* self, PyObject* args)
{
  if (self->shmmode)
    {
      int x,y,w,h, srcoffset, original_w;
      int data_scanline;
      int clipx=0, clipy=0, clipw=65536, cliph=65536;
      code_t* src;
      int length, firstline=0, firstcol=0;
      unsigned int bytes_per_pixel = self->plane.m_shm_image->bits_per_pixel/8;
      unsigned char* data = get_dpy_data(self);
      if (!PyArg_ParseTuple(args, "ii(iis#i)|(iiii)",
                            &x, &y, &w, &h, &src, &length, &srcoffset,
                            &clipx, &clipy, &clipw, &cliph) || !data)
        return NULL;

      original_w = w;
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
      if (x<clipx) { firstcol = clipx-x; w+=x-clipx; x=clipx; }
      if (y<clipy) { firstline = clipy-y; h+=y-clipy; y=clipy; }
      if (x+w > clipw) w = clipw-x;
      if (y+h > cliph) h = cliph-y;
      if (w > 0)
        {
          data += bytes_per_pixel*(x+y*self->width);
          data_scanline = bytes_per_pixel*self->width;

          if (srcoffset < 0)
            {
              /* Format of the data pointed to by 'src':

              [INT] offset to the beginning of the data for line 0
              [INT] offset to the beginning of the data for line 1
              [INT] offset to the beginning of the data for line 2
              ...
              [DATA]

              where DATA is a sequence of blocks:
             
              [BYTE] 0: no-op (padding)
              1: opaque block header
              2: transparent block header
              [BYTE] number of bytes for this block (only for header 1 or 2)
              [n*BYTE] pixel data (only for header 1)
              */

              int* src_offsettable = ((int*) src) + firstline;

              firstcol *= bytes_per_pixel;   /* byte offset within a line */
              w *= bytes_per_pixel;          /* byte offset from firstcol */

              for (y=0; y<h; y++)
                {
                  code_t header;
                  int pixelbytes;
                  int remainingbytes;
                  code_t* source = src + src_offsettable[y];
                  unsigned char* target = data;
                  data += data_scanline;

#define NEXT_BLOCK do {                         \
	while ((header = *source++) == 0) ;     \
        pixelbytes = *source++;                 \
        if (header == 1) source += pixelbytes;  \
} while (0)
#define KEEP_BLOCK_TAIL(n)  (pixelbytes = (n))
#define DATA_BLOCK_START    (source - pixelbytes)

                  /* skip 'firstcol' bytes of data for this line */
                  remainingbytes = firstcol;
                  do {
                    NEXT_BLOCK;
                    remainingbytes -= pixelbytes;
                  } while (remainingbytes > 0);
                  
                  KEEP_BLOCK_TAIL(-remainingbytes);

                  /* copy all blocks until we get near the end */
                  remainingbytes = w;
                  while (remainingbytes > pixelbytes)
                    {
                      if (header == 1)
                        memcpy(target, DATA_BLOCK_START, pixelbytes);
                      target += pixelbytes;
                      remainingbytes -= pixelbytes;
                      NEXT_BLOCK;
                    }

                  /* copy whatever remaining part of the last block we have */
                  if (header == 1)
                    memcpy(target, DATA_BLOCK_START, remainingbytes);
                }
            }
          else
            {
              int scanline = (bytes_per_pixel*original_w + 3)&~3;
              int bytes_per_line = bytes_per_pixel*w;
              src += srcoffset;
              src += firstcol*bytes_per_pixel;
              src += firstline*scanline;
              while (h>0)
                {
                  memcpy(data, src, bytes_per_line);
                  src += scanline;
                  data += data_scanline;
                  h--;
                }
            }
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
      int bytes_per_line, data_scanline;
      int clipx=0, clipy=0, clipw=self->width, cliph=self->height;
      unsigned char* dst;
      int length, dstoffset;
      PyObject* ignored;
      PyObject* result;
      PyObject* str;
      int original_w, original_h;
      unsigned int bytes_per_pixel = self->plane.m_shm_image->bits_per_pixel/8;
      unsigned char* data = get_dpy_data(self);
      if (!PyArg_ParseTuple(args, "(iiii)|O", &x, &y, &w, &h,
                            &ignored) || !data)
        return NULL;

      scanline = (bytes_per_pixel*w + 3)&~3;
      length = scanline*h + 3;
      str = PyString_FromStringAndSize(NULL, length);
      if (!str)
        return NULL;
      dst = (unsigned char*) PyString_AS_STRING(str);
      original_w = w;
      original_h = h;
      
      if (x<clipx) { dst+=(clipx-x)*bytes_per_pixel; w+=x-clipx; x=clipx; }
      if (y<clipy) { dst+=(clipy-y)*scanline; h+=y-clipy; y=clipy; }
      if (x+w > clipw) w = clipw-x;
      if (y+h > cliph) h = cliph-y;
      data += bytes_per_pixel*(x+y*self->width);
      dstoffset = (((long)data) - ((long)dst)) & 3;
      if (w > 0)
        {
          dst += dstoffset;
          bytes_per_line = w*bytes_per_pixel;
          data_scanline = bytes_per_pixel*self->width;
          while (h>0)
            {
              memcpy(dst, data, bytes_per_line);
              dst += scanline;
              data += data_scanline;
              h--;
            }
        }
      result = Py_BuildValue("iiOi", original_w, original_h, str, dstoffset);
      Py_DECREF(str);  /* one ref left in 'result' */
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

static int readXevents(DisplayObject* self)
{
  while (XEventsQueued(self->dpy, QueuedAfterReading) > 0)
    {
      XEvent e;
      XNextEvent(self->dpy, &e);
      switch (e.type) {
      case KeyPress:
      case KeyRelease:
        {
	  KeySym sym;
	  PyObject* v;
          int err;
          if (self->keyevents == NULL)
            {
              self->keyevents = PyList_New(0);
              if (self->keyevents == NULL)
                return 0;
            }
	  sym = XLookupKeysym(&e.xkey,0);
	  v = Py_BuildValue("ii", sym, e.type);
          if (v == NULL)
            return 0;
	  err = PyList_Append(self->keyevents, v);
	  Py_DECREF(v);
	  if (err)
            return 0;
          break;
        }
      case ButtonPress:
        {
	  PyObject* v;
          int err;
          if (self->mouseevents == NULL)
            {
              self->mouseevents = PyList_New(0);
              if (self->mouseevents == NULL)
                return 0;
            }
	  v = Py_BuildValue("ii", e.xbutton.x, e.xbutton.y);
          if (v == NULL)
            return 0;
	  err = PyList_Append(self->mouseevents, v);
	  Py_DECREF(v);
	  if (err)
            return 0;
          break;
        }
      case MotionNotify:
        {
          Py_XDECREF(self->motionevent);
          self->motionevent = Py_BuildValue("ii", e.xmotion.x, e.xmotion.y);
          if (self->motionevent == NULL)
            return 0;
          break;
        }
      }
    }
  return 1;
}

#define ENABLE_EVENTS(mask)     do {                            \
  if (!(self->selectinput & (mask)))                            \
    {                                                           \
      self->selectinput |= (mask);                              \
      XSelectInput(self->dpy, self->win, self->selectinput);    \
    }                                                           \
} while (0)

static PyObject* display_keyevents1(DisplayObject* self, PyObject* args)
{
  PyObject* result;
  ENABLE_EVENTS(KeyPressMask|KeyReleaseMask);
  if (!readXevents(self))
    return NULL;
  result = self->keyevents;
  if (result == NULL)
    result = PyList_New(0);
  else
    self->keyevents = NULL;
  return result;
}

static PyObject* display_mouseevents1(DisplayObject* self, PyObject* args)
{
  PyObject* result;
  ENABLE_EVENTS(ButtonPressMask);
  result = self->mouseevents;
  if (result == NULL)
    result = PyList_New(0);
  else
    self->mouseevents = NULL;
  return result;
}

static PyObject* display_pointermotion1(DisplayObject* self, PyObject* args)
{
  PyObject* result;
  ENABLE_EVENTS(PointerMotionMask);
  result = self->motionevent;
  if (result == NULL)
    {
      Py_INCREF(Py_None);
      result = Py_None;
    }
  else
    self->motionevent = NULL;
  return result;
}

static PyObject* display_flip1(DisplayObject* self, PyObject* args)
{
  if (!checkopen(self))
    return NULL;

  if (self->shmmode)
    {
      XShmPutImage(self->dpy, self->win, self->gc,
                   self->plane.m_shm_image,
                   0, 0, 0, 0,
                   self->plane.m_width,
                   self->plane.m_height,
                   False);
    }
  else
    {
      XCopyArea(self->dpy, self->backpixmap, self->win, self->gc,
                0, 0, self->width, self->height, 0, 0);
    }
  flush(self);
  if (!readXevents(self))
    return NULL;
  Py_INCREF(Py_None);
  return Py_None;
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
