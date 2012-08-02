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

#include "gtk-notification.h"

/**
 * SECTION:gtknotification
 * @short_description: Report notification messages to the user
 * @include: gtk/gtk.h
 * @see_also: #GtkStatusbar, #GtkMessageDialog, #GtkInfoBar
 *
 * #GtkNotification is a widget made for showing notifications to
 * the user, allowing them to close the notification or wait for it
 * to time out.
 *
 * #GtkNotification provides one signal (#GtkNotification::dismissed), for when the notification
 * times out or is closed.
 *
 */

#define GTK_PARAM_READWRITE G_PARAM_READWRITE|G_PARAM_STATIC_NAME|G_PARAM_STATIC_NICK|G_PARAM_STATIC_BLURB
#define SHADOW_OFFSET_X 2
#define SHADOW_OFFSET_Y 3
#define ANIMATION_TIME 200 /* msec */
#define ANIMATION_STEP 40 /* msec */

enum {
  PROP_0,
  PROP_TIMEOUT
};

struct _GtkNotificationPrivate {
  GtkWidget *close_button;

  GdkWindow *bin_window;

  int animate_y; /* from 0 to allocation.height */
  gboolean waiting_for_viewable;
  gboolean revealed;
  gboolean dismissed;
  gboolean sent_dismissed;
  guint animate_timeout;

  guint timeout;
  guint timeout_source_id;
};

enum {
  DISMISSED,
  LAST_SIGNAL
};

static guint notification_signals[LAST_SIGNAL] = { 0 };

static gboolean gtk_notification_draw                           (GtkWidget       *widget,
                                                                 cairo_t         *cr);
static void     gtk_notification_get_preferred_width            (GtkWidget       *widget,
                                                                 gint            *minimum_size,
                                                                 gint            *natural_size);
static void     gtk_notification_get_preferred_height_for_width (GtkWidget       *widget,
                                                                 gint             width,
                                                                 gint            *minimum_height,
                                                                 gint            *natural_height);
static void     gtk_notification_get_preferred_height           (GtkWidget       *widget,
                                                                 gint            *minimum_size,
                                                                 gint            *natural_size);
static void     gtk_notification_get_preferred_width_for_height (GtkWidget       *widget,
                                                                 gint             height,
                                                                 gint            *minimum_width,
                                                                 gint            *natural_width);
static void     gtk_notification_size_allocate                  (GtkWidget       *widget,
                                                                 GtkAllocation   *allocation);
static gboolean gtk_notification_timeout_cb                     (gpointer         user_data);
static void     gtk_notification_style_updated                  (GtkWidget       *widget);
static void     gtk_notification_show                           (GtkWidget       *widget);
static void     gtk_notification_add                            (GtkContainer    *container,
                                                                 GtkWidget       *child);

/* signals handlers */
static void     gtk_notification_close_button_clicked_cb        (GtkWidget       *widget,
                                                                 gpointer         user_data);
static void     gtk_notification_action_button_clicked_cb       (GtkWidget       *widget,
                                                                 gpointer         user_data);


G_DEFINE_TYPE(GtkNotification, gtk_notification, GTK_TYPE_BIN);

static void
gtk_notification_init (GtkNotification *notification)
{
  GtkWidget *close_button_image;
  GtkStyleContext *context;
  GtkNotificationPrivate *priv;

  context = gtk_widget_get_style_context (GTK_WIDGET (notification));
  gtk_style_context_add_class (context, "contacts-notification");


  gtk_widget_set_halign (GTK_WIDGET (notification), GTK_ALIGN_CENTER);
  gtk_widget_set_valign (GTK_WIDGET (notification), GTK_ALIGN_START);

  gtk_widget_set_has_window (GTK_WIDGET (notification), TRUE);

  gtk_widget_push_composite_child ();

  priv = notification->priv =
    G_TYPE_INSTANCE_GET_PRIVATE (notification,
                                 GTK_TYPE_NOTIFICATION,
                                 GtkNotificationPrivate);

  priv->animate_y = 0;
  priv->close_button = gtk_button_new ();
  gtk_widget_set_parent (priv->close_button, GTK_WIDGET (notification));
  gtk_widget_show (priv->close_button);
  g_object_set (priv->close_button,
                "relief", GTK_RELIEF_NONE,
                "focus-on-click", FALSE,
                NULL);
  g_signal_connect (priv->close_button,
                    "clicked",
                    G_CALLBACK (gtk_notification_close_button_clicked_cb),
                    notification);
  close_button_image = gtk_image_new_from_icon_name ("window-close-symbolic", GTK_ICON_SIZE_BUTTON);
  gtk_button_set_image (GTK_BUTTON (notification->priv->close_button), close_button_image);

  gtk_widget_pop_composite_child ();

  priv->timeout_source_id = 0;
}

static void
gtk_notification_finalize (GObject *object)
{
  GtkNotification *notification;
  GtkNotificationPrivate *priv;

  g_return_if_fail (GTK_IS_NOTIFICATION (object));

  notification = GTK_NOTIFICATION (object);
  priv = notification->priv;

  if (priv->animate_timeout != 0)
    g_source_remove (priv->animate_timeout);

  if (priv->timeout_source_id != 0)
    g_source_remove (priv->timeout_source_id);

  G_OBJECT_CLASS (gtk_notification_parent_class)->finalize (object);
}

static void
gtk_notification_destroy (GtkWidget *widget)
{
  GtkNotification *notification = GTK_NOTIFICATION (widget);
  GtkNotificationPrivate *priv = notification->priv;

  if (!priv->sent_dismissed)
    {
      g_signal_emit (notification, notification_signals[DISMISSED], 0);
      priv->sent_dismissed = TRUE;
    }

  if (priv->close_button)
    {
      gtk_widget_unparent (priv->close_button);
      priv->close_button = NULL;
    }

  GTK_WIDGET_CLASS (gtk_notification_parent_class)->destroy (widget);
}

static void
gtk_notification_realize (GtkWidget *widget)
{
  GtkNotification *notification = GTK_NOTIFICATION (widget);
  GtkNotificationPrivate *priv = notification->priv;
  GtkBin *bin = GTK_BIN (widget);
  GtkAllocation allocation;
  GtkAllocation view_allocation;
  GtkStyleContext *context;
  GtkWidget *child;
  GdkWindow *window;
  GdkWindowAttr attributes;
  gint attributes_mask;
  gint event_mask;

  gtk_widget_set_realized (widget, TRUE);

  gtk_widget_get_allocation (widget, &allocation);

  attributes.x = allocation.x;
  attributes.y = allocation.y;
  attributes.width = allocation.width;
  attributes.height = allocation.height;
  attributes.window_type = GDK_WINDOW_CHILD;
  attributes.wclass = GDK_INPUT_OUTPUT;
  attributes.visual = gtk_widget_get_visual (widget);

  attributes.event_mask = GDK_VISIBILITY_NOTIFY_MASK | GDK_EXPOSURE_MASK;

  attributes_mask = GDK_WA_X | GDK_WA_Y | GDK_WA_VISUAL;

  window = gdk_window_new (gtk_widget_get_parent_window (widget),
                           &attributes, attributes_mask);
  gtk_widget_set_window (widget, window);
  gdk_window_set_user_data (window, notification);

  attributes.x = 0;
  attributes.y = attributes.height + priv->animate_y;
  attributes.event_mask = gtk_widget_get_events (widget) | GDK_EXPOSURE_MASK | GDK_VISIBILITY_NOTIFY_MASK;

  priv->bin_window = gdk_window_new (window, &attributes, attributes_mask);
  gdk_window_set_user_data (priv->bin_window, notification);

  child = gtk_bin_get_child (bin);
  if (child)
    gtk_widget_set_parent_window (child, priv->bin_window);
  gtk_widget_set_parent_window (priv->close_button, priv->bin_window);

  context = gtk_widget_get_style_context (widget);
  gtk_style_context_set_background (context, window);
  gtk_style_context_set_background (context, priv->bin_window);

  gdk_window_show (priv->bin_window);
}

static void
gtk_notification_unrealize (GtkWidget *widget)
{
  GtkNotification *notification = GTK_NOTIFICATION (widget);
  GtkNotificationPrivate *priv = notification->priv;

  gdk_window_set_user_data (priv->bin_window, NULL);
  gdk_window_destroy (priv->bin_window);
  priv->bin_window = NULL;

  GTK_WIDGET_CLASS (gtk_notification_parent_class)->unrealize (widget);
}

static int
animation_target (GtkNotification *notification)
{
  GtkNotificationPrivate *priv = notification->priv;
  GtkAllocation allocation;

  if (priv->revealed) {
    gtk_widget_get_allocation (GTK_WIDGET (notification), &allocation);
    return allocation.height;
  } else {
    return 0;
  }
}

static gboolean
animation_timeout_cb (gpointer user_data)
{
  GtkNotification *notification = GTK_NOTIFICATION (user_data);
  GtkNotificationPrivate *priv = notification->priv;
  GtkAllocation allocation;
  int target, delta;

  target = animation_target (notification);

  if (priv->animate_y != target) {
    gtk_widget_get_allocation (GTK_WIDGET (notification), &allocation);

    delta = allocation.height * ANIMATION_STEP / ANIMATION_TIME;

    if (priv->revealed)
      priv->animate_y += delta;
    else
      priv->animate_y -= delta;

    priv->animate_y = CLAMP (priv->animate_y, 0, allocation.height);

    if (priv->bin_window != NULL)
      gdk_window_move (priv->bin_window,
                       0,
                       -allocation.height + priv->animate_y);
    return TRUE;
  }

  if (priv->dismissed && priv->animate_y == 0)
    gtk_widget_destroy (GTK_WIDGET (notification));

  priv->animate_timeout = 0;
  return FALSE;
}

static void
start_animation (GtkNotification *notification)
{
  GtkNotificationPrivate *priv = notification->priv;
  int target;

  if (priv->animate_timeout != 0)
    return; /* Already running */

  target = animation_target (notification);
  if (priv->animate_y != target)
    notification->priv->animate_timeout =
      gdk_threads_add_timeout (ANIMATION_STEP,
                               animation_timeout_cb,
                               notification);
}

static void
gtk_notification_show (GtkWidget *widget)
{
  GtkNotification *notification = GTK_NOTIFICATION (widget);
  GtkNotificationPrivate *priv = notification->priv;

  GTK_WIDGET_CLASS (gtk_notification_parent_class)->show (widget);
  priv->revealed = TRUE;
  priv->waiting_for_viewable = TRUE;
}

static void
gtk_notification_hide (GtkWidget *widget)
{
  GtkNotification *notification = GTK_NOTIFICATION (widget);
  GtkNotificationPrivate *priv = notification->priv;

  GTK_WIDGET_CLASS (gtk_notification_parent_class)->hide (widget);
  priv->revealed = FALSE;
  priv->waiting_for_viewable = FALSE;
}

static void
gtk_notification_set_property (GObject *object, guint prop_id, const GValue *value, GParamSpec *pspec)
{
  GtkNotification *notification = GTK_NOTIFICATION (object);

  g_return_if_fail (GTK_IS_NOTIFICATION (object));

  switch (prop_id) {
  case PROP_TIMEOUT:
    gtk_notification_set_timeout (notification,
                                  g_value_get_uint (value));
    break;
  default:
    G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
    break;
  }
}

static void
gtk_notification_get_property (GObject *object, guint prop_id, GValue *value, GParamSpec *pspec)
{
  g_return_if_fail (GTK_IS_NOTIFICATION (object));
  GtkNotification *notification = GTK_NOTIFICATION (object);

  switch (prop_id) {
  case PROP_TIMEOUT:
    g_value_set_uint (value, notification->priv->timeout);
    break;
  default:
    G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
    break;
  }
}

static void
gtk_notification_forall (GtkContainer *container,
                         gboolean      include_internals,
                         GtkCallback   callback,
                         gpointer      callback_data)
{
  GtkBin *bin = GTK_BIN (container);
  GtkNotification *notification = GTK_NOTIFICATION (container);
  GtkNotificationPrivate *priv = notification->priv;
  GtkWidget *child;

  child = gtk_bin_get_child (bin);
  if (child)
    (* callback) (child, callback_data);

  if (include_internals)
    (* callback) (priv->close_button, callback_data);
}

static gboolean
gtk_notification_visibility_notify_event (GtkWidget          *widget,
                                          GdkEventVisibility  *event)
{
  GtkNotification *notification = GTK_NOTIFICATION (widget);
  GtkNotificationPrivate *priv = notification->priv;

  if (priv->waiting_for_viewable)
    {
      start_animation (notification);
      priv->waiting_for_viewable = FALSE;
    }

  if (notification->priv->timeout_source_id == 0)
    notification->priv->timeout_source_id =
      gdk_threads_add_timeout (notification->priv->timeout * 1000,
                               gtk_notification_timeout_cb,
                               widget);

  return FALSE;
}

static void
gtk_notification_class_init (GtkNotificationClass *klass)
{
  GObjectClass* object_class = G_OBJECT_CLASS (klass);
  GtkWidgetClass* widget_class = GTK_WIDGET_CLASS(klass);
  GtkContainerClass *container_class = GTK_CONTAINER_CLASS (klass);

  object_class->finalize = gtk_notification_finalize;
  object_class->set_property = gtk_notification_set_property;
  object_class->get_property = gtk_notification_get_property;

  widget_class->show = gtk_notification_show;
  widget_class->destroy = gtk_notification_destroy;
  widget_class->get_preferred_width = gtk_notification_get_preferred_width;
  widget_class->get_preferred_height_for_width = gtk_notification_get_preferred_height_for_width;
  widget_class->get_preferred_height = gtk_notification_get_preferred_height;
  widget_class->get_preferred_width_for_height = gtk_notification_get_preferred_width_for_height;
  widget_class->size_allocate = gtk_notification_size_allocate;
  widget_class->draw = gtk_notification_draw;
  widget_class->realize = gtk_notification_realize;
  widget_class->unrealize = gtk_notification_unrealize;
  widget_class->style_updated = gtk_notification_style_updated;
  widget_class->visibility_notify_event = gtk_notification_visibility_notify_event;

  container_class->add = gtk_notification_add;
  container_class->forall = gtk_notification_forall;
  gtk_container_class_handle_border_width (container_class);


  /**
   * GtkNotification:timeout:
   *
   * The time it takes to hide the widget, in seconds.
   *
   * Since: 0.1
   */
  g_object_class_install_property (object_class,
                                   PROP_TIMEOUT,
                                   g_param_spec_uint("timeout", "timeout",
                                                     "The time it takes to hide the widget, in seconds",
                                                     0, G_MAXUINT, 10,
                                                     GTK_PARAM_READWRITE | G_PARAM_CONSTRUCT));

  notification_signals[DISMISSED] = g_signal_new ("dismissed",
                                                  G_OBJECT_CLASS_TYPE (klass),
                                                  G_SIGNAL_RUN_LAST,
                                                  G_STRUCT_OFFSET (GtkNotificationClass, dismissed),
                                                  NULL,
                                                  NULL,
                                                  g_cclosure_marshal_VOID__VOID,
                                                  G_TYPE_NONE,
                                                  0);

  g_type_class_add_private (object_class, sizeof (GtkNotificationPrivate));
}

static void
draw_shadow_box (cairo_t *cr, GdkRectangle rect, int left_border, int right_border,
                 int bottom_border, double inner_alpha)
{
  cairo_pattern_t *pattern;
  cairo_matrix_t matrix;
  double x0, x1, x2, x3;
  double y0, y2, y3;

  cairo_save (cr);

  x0 = rect.x;
  x1 = rect.x + left_border;
  x2 = rect.x + rect.width - right_border;
  x3 = rect.x + rect.width;

  y0 = rect.y;
  y2 = rect.y + rect.height - bottom_border;
  y3 = rect.y + rect.height;

  /* Bottom border */

  pattern = cairo_pattern_create_linear(0, y2, 0, y3);

  cairo_pattern_add_color_stop_rgba(pattern, 0.0, 0, 0, 0, inner_alpha);
  cairo_pattern_add_color_stop_rgba(pattern, 1.0, 0, 0, 0, 0.0);

  cairo_set_source(cr, pattern);
  cairo_pattern_destroy(pattern);

  cairo_rectangle(cr, x1, y2, x2 - x1, y3 - y2);
  cairo_fill(cr);

  /* Left border */

  pattern = cairo_pattern_create_linear(x0, 0, x1, 0);

  cairo_pattern_add_color_stop_rgba(pattern, 0.0, 0, 0, 0, 0.0);
  cairo_pattern_add_color_stop_rgba(pattern, 1.0, 0, 0, 0, inner_alpha);

  cairo_set_source(cr, pattern);
  cairo_pattern_destroy(pattern);

  cairo_rectangle(cr, x0, y0, x1 - x0, y2 - y0);
  cairo_fill(cr);

  /* Right border */

  pattern = cairo_pattern_create_linear(x2, 0, x3, 0);

  cairo_pattern_add_color_stop_rgba(pattern, 0.0, 0, 0, 0, inner_alpha);
  cairo_pattern_add_color_stop_rgba(pattern, 1.0, 0, 0, 0, 0.0);

  cairo_set_source(cr, pattern);
  cairo_pattern_destroy(pattern);

  cairo_rectangle(cr, x2, y0, x3 - x2, y2 - y0);
  cairo_fill(cr);

  /* SW corner */

  pattern = cairo_pattern_create_radial(0, 0, 0, 0.0, 0, 1.0);
  cairo_pattern_add_color_stop_rgba(pattern, 0.0, 0, 0, 0, inner_alpha);
  cairo_pattern_add_color_stop_rgba(pattern, 1.0, 0, 0, 0, 0.0);

  cairo_matrix_init_scale (&matrix, 1.0 / left_border, 1.0 / bottom_border);
  cairo_matrix_translate (&matrix, - x1, -y2);
  cairo_pattern_set_matrix (pattern, &matrix);

  cairo_set_source(cr, pattern);
  cairo_pattern_destroy(pattern);

  cairo_rectangle(cr, x0, y2, x1 - x0, y3 - y2);
  cairo_fill(cr);

  /* SE corner */

  pattern = cairo_pattern_create_radial(0, 0, 0, 0, 0, 1.0);
  cairo_pattern_add_color_stop_rgba(pattern, 0.0, 0.0, 0, 0, inner_alpha);
  cairo_pattern_add_color_stop_rgba(pattern, 1.0, 0.0, 0, 0, 0.0);

  cairo_matrix_init_scale (&matrix, 1.0 / left_border, 1.0 / bottom_border);
  cairo_matrix_translate (&matrix, - x2, -y2);
  cairo_pattern_set_matrix (pattern, &matrix);

  cairo_set_source(cr, pattern);
  cairo_pattern_destroy(pattern);

  cairo_rectangle(cr, x2, y2, x3 - x2, y3 - y2);
  cairo_fill(cr);

  cairo_restore (cr);
}

static void
get_padding_and_border (GtkNotification *notification,
                        GtkBorder *border)
{
  GtkStyleContext *context;
  GtkStateFlags state;
  GtkBorder tmp;

  context = gtk_widget_get_style_context (GTK_WIDGET (notification));
  state = gtk_widget_get_state_flags (GTK_WIDGET (notification));

  gtk_style_context_get_padding (context, state, border);

  gtk_style_context_get_border (context, state, &tmp);
  border->top += tmp.top;
  border->right += tmp.right;
  border->bottom += tmp.bottom;
  border->left += tmp.left;
}

static gboolean
gtk_notification_draw (GtkWidget *widget, cairo_t *cr)
{
  GtkNotification *notification = GTK_NOTIFICATION (widget);
  GtkNotificationPrivate *priv = notification->priv;
  GtkStyleContext *context;
  GdkRectangle rect;
  int inner_radius;

  if (gtk_cairo_should_draw_window (cr, priv->bin_window))
    {
      gtk_widget_get_allocation (widget, &rect);

      context = gtk_widget_get_style_context(widget);

      inner_radius = 5;
      draw_shadow_box (cr, rect, SHADOW_OFFSET_X + inner_radius, SHADOW_OFFSET_X + inner_radius,
                       SHADOW_OFFSET_Y + inner_radius, 0.8);

      gtk_style_context_save (context);
      gtk_render_background (context,  cr,
                             SHADOW_OFFSET_X, 0,
                             gtk_widget_get_allocated_width (widget) - 2 *SHADOW_OFFSET_X,
                             gtk_widget_get_allocated_height (widget) - SHADOW_OFFSET_Y);
      gtk_render_frame (context,cr,
                        SHADOW_OFFSET_X, 0,
                        gtk_widget_get_allocated_width (widget) - 2 *SHADOW_OFFSET_X,
                        gtk_widget_get_allocated_height (widget) - SHADOW_OFFSET_Y);

      gtk_style_context_restore (context);

      if (GTK_WIDGET_CLASS (gtk_notification_parent_class)->draw)
        GTK_WIDGET_CLASS (gtk_notification_parent_class)->draw(widget, cr);
    }

  return FALSE;
}

static void
gtk_notification_add (GtkContainer *container,
                      GtkWidget    *child)
{
  GtkBin *bin = GTK_BIN (container);
  GtkNotification *notification = GTK_NOTIFICATION (bin);
  GtkNotificationPrivate *priv = notification->priv;

  g_return_if_fail (gtk_bin_get_child (bin) == NULL);

  gtk_widget_set_parent_window (child, priv->bin_window);

  GTK_CONTAINER_CLASS (gtk_notification_parent_class)->add (container, child);
}


static void
gtk_notification_get_preferred_width (GtkWidget *widget, gint *minimum_size, gint *natural_size)
{
  GtkNotification *notification = GTK_NOTIFICATION (widget);
  GtkNotificationPrivate *priv = notification->priv;
  GtkBin *bin = GTK_BIN (widget);
  gint child_min, child_nat;
  GtkWidget *child;
  GtkBorder padding;
  gint minimum, natural;

  get_padding_and_border (notification, &padding);

  minimum = 0;
  natural = 0;

  child = gtk_bin_get_child (bin);
  if (child && gtk_widget_get_visible (child))
    {
      gtk_widget_get_preferred_width (child,
                                      &child_min, &child_nat);
      minimum += child_min;
      natural += child_nat;
    }

  gtk_widget_get_preferred_width (priv->close_button,
                                  &child_min, &child_nat);
  minimum += child_min;
  natural += child_nat;


  minimum += padding.left + padding.right + 2 * SHADOW_OFFSET_X;
  natural += padding.left + padding.right + 2 * SHADOW_OFFSET_X;

 if (minimum_size)
    *minimum_size = minimum;

  if (natural_size)
    *natural_size = natural;
}

static void
gtk_notification_get_preferred_width_for_height (GtkWidget *widget,
                                                 gint height,
                                                 gint *minimum_width,
                                                 gint *natural_width)
{
  GtkNotification *notification = GTK_NOTIFICATION (widget);
  GtkNotificationPrivate *priv = notification->priv;
  GtkBin *bin = GTK_BIN (widget);
  gint child_min, child_nat, child_height;
  GtkWidget *child;
  GtkBorder padding;
  gint minimum, natural;

  get_padding_and_border (notification, &padding);

  minimum = 0;
  natural = 0;

  child_height = height - SHADOW_OFFSET_Y - padding.top - padding.bottom;

  child = gtk_bin_get_child (bin);
  if (child && gtk_widget_get_visible (child))
    {
      gtk_widget_get_preferred_width_for_height (child, child_height,
                                                 &child_min, &child_nat);
      minimum += child_min;
      natural += child_nat;
    }

  gtk_widget_get_preferred_width_for_height (priv->close_button, child_height,
                                             &child_min, &child_nat);
  minimum += child_min;
  natural += child_nat;

  minimum += padding.left + padding.right + 2 * SHADOW_OFFSET_X;
  natural += padding.left + padding.right + 2 * SHADOW_OFFSET_X;

 if (minimum_width)
    *minimum_width = minimum;

  if (natural_width)
    *natural_width = natural;
}

static void
gtk_notification_get_preferred_height_for_width (GtkWidget *widget,
                                                 gint width,
                                                 gint *minimum_height,
                                                 gint *natural_height)
{
  GtkNotification *notification = GTK_NOTIFICATION (widget);
  GtkNotificationPrivate *priv = notification->priv;
  GtkBin *bin = GTK_BIN (widget);
  gint child_min, child_nat, child_width, button_width;
  GtkWidget *child;
  GtkBorder padding;
  gint minimum, natural;

  get_padding_and_border (notification, &padding);

  gtk_widget_get_preferred_height (priv->close_button,
                                   &minimum, &natural);
  gtk_widget_get_preferred_width (priv->close_button,
                                  NULL, &button_width);

  child = gtk_bin_get_child (bin);
  if (child && gtk_widget_get_visible (child))
    {
      child_width = width - 2 * SHADOW_OFFSET_X - padding.left - padding.top - button_width;

      gtk_widget_get_preferred_height_for_width (child, child_width,
                                                 &child_min, &child_nat);
      minimum = MAX (minimum, child_min);
      natural = MAX (natural, child_nat);
    }

  minimum += padding.top + padding.top + SHADOW_OFFSET_Y;
  natural += padding.top + padding.top + SHADOW_OFFSET_Y;

 if (minimum_height)
    *minimum_height = minimum;

  if (natural_height)
    *natural_height = natural;
}

static void
gtk_notification_get_preferred_height (GtkWidget *widget, gint *minimum_height, gint *natural_height)
{
  GtkNotification *notification = GTK_NOTIFICATION (widget);
  GtkNotificationPrivate *priv = notification->priv;
  GtkBin *bin = GTK_BIN (widget);
  gint child_min, child_nat;
  GtkWidget *child;
  GtkBorder padding;
  gint minimum, natural;

  get_padding_and_border (notification, &padding);

  gtk_widget_get_preferred_height (priv->close_button,
                                   &minimum, &natural);

  child = gtk_bin_get_child (bin);
  if (child && gtk_widget_get_visible (child))
    {
      gtk_widget_get_preferred_height (child,
                                       &child_min, &child_nat);
      minimum = MAX (minimum, child_min);
      natural = MAX (natural, child_nat);
    }

  minimum += padding.top + padding.top + SHADOW_OFFSET_Y;
  natural += padding.top + padding.top + SHADOW_OFFSET_Y;

 if (minimum_height)
    *minimum_height = minimum;

  if (natural_height)
    *natural_height = natural;
}

static void
gtk_notification_size_allocate (GtkWidget *widget,
                                GtkAllocation *allocation)
{
  GtkNotification *notification = GTK_NOTIFICATION (widget);
  GtkNotificationPrivate *priv = notification->priv;
  GtkBin *bin = GTK_BIN (widget);
  GtkAllocation child_allocation;
  GtkBorder padding;
  GtkWidget *child;
  int button_width;

  gtk_widget_set_allocation (widget, allocation);

  /* If somehow the notification changes while not hidden
     and we're not animating, immediately follow the resize */
  if (priv->animate_y > 0 &&
      !priv->animate_timeout)
    priv->animate_y = allocation->height;

  get_padding_and_border (notification, &padding);

  if (gtk_widget_get_realized (widget))
    {
      gdk_window_move_resize (gtk_widget_get_window (widget),
                              allocation->x,
                              allocation->y,
                              allocation->width,
                              allocation->height);
      gdk_window_move_resize (priv->bin_window,
                              0,
                              -allocation->height + priv->animate_y,
                              allocation->width,
                              allocation->height);
    }

  child_allocation.x = SHADOW_OFFSET_X + padding.left;
  child_allocation.y = padding.top;
  child_allocation.height = MAX (1, allocation->height - SHADOW_OFFSET_Y - padding.top - padding.bottom);
  gtk_widget_get_preferred_width_for_height (priv->close_button, child_allocation.height,
                                             NULL, &button_width);

  child_allocation.width = MAX (1, allocation->width - 2 * SHADOW_OFFSET_X - padding.left - padding.right - button_width);

  child = gtk_bin_get_child (bin);
  if (child && gtk_widget_get_visible (child))
    gtk_widget_size_allocate (child, &child_allocation);

  child_allocation.x += child_allocation.width;
  child_allocation.width = button_width;

  gtk_widget_size_allocate (priv->close_button, &child_allocation);
}

static gboolean
gtk_notification_timeout_cb (gpointer user_data)
{
  GtkNotification *notification = GTK_NOTIFICATION (user_data);

  gtk_notification_dismiss (notification);

  return FALSE;
}

static void
gtk_notification_style_updated (GtkWidget *widget)
{
   GTK_WIDGET_CLASS (gtk_notification_parent_class)->style_updated (widget);

   if (gtk_widget_get_realized (widget))
     {
        GtkStyleContext *context;
        GtkNotification *notification = GTK_NOTIFICATION (widget);
        GtkNotificationPrivate *priv = notification->priv;

        context = gtk_widget_get_style_context (widget);
        gtk_style_context_set_background (context, priv->bin_window);
        gtk_style_context_set_background (context, gtk_widget_get_window (widget));
     }
}

void
gtk_notification_set_timeout (GtkNotification *notification,
                              guint            timeout_msec)
{
  GtkNotificationPrivate *priv = notification->priv;

  priv->timeout = timeout_msec;
  g_object_notify (G_OBJECT (notification), "timeout");
}

void
gtk_notification_dismiss (GtkNotification *notification)
{
  GtkNotificationPrivate *priv = notification->priv;

  if (notification->priv->timeout_source_id)
    {
      g_source_remove (notification->priv->timeout_source_id);
      notification->priv->timeout_source_id = 0;
    }

  priv->dismissed = TRUE;
  priv->revealed = FALSE;
  start_animation (notification);
}

static void
gtk_notification_close_button_clicked_cb (GtkWidget *widget, gpointer user_data)
{
  GtkNotification *notification = GTK_NOTIFICATION(user_data);
  GtkNotificationPrivate *priv = notification->priv;

  gtk_notification_dismiss (notification);
}

GtkWidget *
gtk_notification_new (void)
{
  return g_object_new (GTK_TYPE_NOTIFICATION, NULL);
}
