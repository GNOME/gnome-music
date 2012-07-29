[CCode (cprefix = "Gtk", lower_case_cprefix = "gtk_", cheader_filename = "gtk-notification.h")]
namespace Gtk {
	public class Notification : Gtk.Box {
		[CCode (has_construct_function = false, type = "GtkWidget*")]
		public Notification ();
		public void set_timeout (uint timeout_msec);
		public void dismiss ();
		public virtual signal void dismissed ();
	}
	[CCode (cname = "gtk_builder_add_from_resource")]
	public static unowned uint my_builder_add_from_resource (Gtk.Builder builder, string path) throws GLib.Error;
}
