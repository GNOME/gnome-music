/*
 * Copyright (c) 2012 Red Hat, Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
 * or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public
 * License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this program; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
 *
 */

#ifndef __GD_H__
#define __GD_H__

#include <glib-object.h>

G_BEGIN_DECLS

#include <libgd/gd-types-catalog.h>

#ifdef LIBGD_GTK_HACKS
# include <libgd/gd-icon-utils.h>
#endif

#ifdef LIBGD__BOX_COMMON
# include <libgd/gd-main-box-child.h>
# include <libgd/gd-main-box-generic.h>
# include <libgd/gd-main-box-item.h>
#endif

#ifdef LIBGD_MAIN_ICON_BOX
# include <libgd/gd-main-icon-box.h>
# include <libgd/gd-main-icon-box-child.h>
#endif

#ifdef LIBGD_MAIN_BOX
# include <libgd/gd-main-box.h>
#endif

#ifdef LIBGD__VIEW_COMMON
# include <libgd/gd-main-view-generic.h>
# include <libgd/gd-styled-text-renderer.h>
# include <libgd/gd-two-lines-renderer.h>
#endif

#ifdef LIBGD_MAIN_ICON_VIEW
# include <libgd/gd-main-icon-view.h>
# include <libgd/gd-toggle-pixbuf-renderer.h>
#endif

#ifdef LIBGD_MAIN_LIST_VIEW
# include <libgd/gd-main-list-view.h>
#endif

#ifdef LIBGD_MAIN_VIEW
# include <libgd/gd-main-view.h>
#endif

#ifdef LIBGD_MARGIN_CONTAINER
# include <libgd/gd-margin-container.h>
#endif

#ifdef LIBGD_TAGGED_ENTRY
# include <libgd/gd-tagged-entry.h>
#endif

#ifdef LIBGD_NOTIFICATION
# include <libgd/gd-notification.h>
#endif

G_END_DECLS

#endif /* __GD_H__ */
