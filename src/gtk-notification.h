/* -*- Mode: C; tab-width: 8; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
/*
 * gtk-notification.c
 * Copyright (C) Erick Pérez Castellanos 2011 <erick.red@gmail.com>
 *
 gtk-notification.c is free software: you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as published
 * by the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * gtk-notification.c is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 * See the GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.";
 */

#ifndef _GTK_NOTIFICATION_H_
#define _GTK_NOTIFICATION_H_

#include <gtk/gtk.h>

G_BEGIN_DECLS

#define GTK_TYPE_NOTIFICATION             (gtk_notification_get_type ())
#define GTK_NOTIFICATION(obj)             (G_TYPE_CHECK_INSTANCE_CAST ((obj), GTK_TYPE_NOTIFICATION, GtkNotification))
#define GTK_NOTIFICATION_CLASS(klass)     (G_TYPE_CHECK_CLASS_CAST ((klass), GTK_TYPE_NOTIFICATION, GtkNotificationClass))
#define GTK_IS_NOTIFICATION(obj)          (G_TYPE_CHECK_INSTANCE_TYPE ((obj), GTK_TYPE_NOTIFICATION))
#define GTK_IS_NOTIFICATION_CLASS(klass)  (G_TYPE_CHECK_CLASS_TYPE ((klass), GTK_TYPE_NOTIFICATION))
#define GTK_NOTIFICATION_GET_CLASS(obj)   (G_TYPE_INSTANCE_GET_CLASS ((obj), GTK_TYPE_NOTIFICATION, GtkNotificationClass))

typedef struct _GtkNotificationPrivate GtkNotificationPrivate;
typedef struct _GtkNotificationClass GtkNotificationClass;
typedef struct _GtkNotification GtkNotification;

struct _GtkNotificationClass {
  GtkBinClass parent_class;

  /* Signals */
  void (*dismissed) (GtkNotification *self);
};

struct _GtkNotification {
  GtkBin parent_instance;

  /*< private > */
  GtkNotificationPrivate *priv;
};

GType gtk_notification_get_type (void) G_GNUC_CONST;

GtkWidget *gtk_notification_new         (void);
void       gtk_notification_set_timeout (GtkNotification *notification,
                                         guint            timeout_msec);
void       gtk_notification_dismiss     (GtkNotification *notification);

G_END_DECLS

#endif /* _GTK_NOTIFICATION_H_ */
