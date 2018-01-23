#include <gtk/gtk.h>
#include <libgd/gd-tagged-entry.h>

static GdTaggedEntryTag *toggle_tag;

static void
on_tag_clicked (GdTaggedEntry *entry,
                GdTaggedEntryTag *tag,
                gpointer useless)
{
  g_print ("tag clicked: %s\n", gd_tagged_entry_tag_get_label (tag));
}

static void
on_tag_button_clicked (GdTaggedEntry *entry,
                       GdTaggedEntryTag *tag,
                       gpointer useless)
{
  g_print ("tag button clicked: %s\n", gd_tagged_entry_tag_get_label (tag));
}

static void
on_toggle_visible (GtkButton *button,
                   GtkWidget *entry)
{
  gboolean active;

  active = gtk_toggle_button_get_active (GTK_TOGGLE_BUTTON (button));

  g_print ("%s tagged entry\n", active ? "show" : "hide");
  gtk_widget_set_visible (entry, active);
}

static void
on_toggle_tag (GtkButton *button,
               GdTaggedEntry *entry)
{
  gboolean active;

  active = gtk_toggle_button_get_active (GTK_TOGGLE_BUTTON (button));

  if (active)
    {
      g_print ("adding tag 'Toggle Tag'\n");
      gd_tagged_entry_insert_tag (entry, toggle_tag, 0);
    }
  else
    {
      g_print ("removing tag 'Toggle Tag'\n");
      gd_tagged_entry_remove_tag (entry, toggle_tag);
    }
}

gint
main (gint argc,
      gchar ** argv)
{
  GtkWidget *window, *box, *entry, *toggle_visible_button, *toggle_tag_button;
  GdTaggedEntryTag *tag;

  gtk_init (&argc, &argv);

  window = gtk_window_new (GTK_WINDOW_TOPLEVEL);
  gtk_widget_set_size_request (window, 300, 0);

  box = gtk_box_new (GTK_ORIENTATION_VERTICAL, 0);
  gtk_container_add (GTK_CONTAINER (window), box);

  entry = GTK_WIDGET (gd_tagged_entry_new ());
  g_signal_connect(entry, "tag-clicked",
                   G_CALLBACK (on_tag_clicked), NULL);
  g_signal_connect(entry, "tag-button-clicked",
                   G_CALLBACK (on_tag_button_clicked), NULL);
  gtk_container_add (GTK_CONTAINER (box), entry);

  tag = gd_tagged_entry_tag_new ("Blah1");
  gd_tagged_entry_add_tag (GD_TAGGED_ENTRY (entry), tag);
  g_object_unref (tag);

  tag = gd_tagged_entry_tag_new ("Blah2");
  gd_tagged_entry_tag_set_has_close_button (tag, FALSE);
  gd_tagged_entry_insert_tag (GD_TAGGED_ENTRY (entry), tag, -1);
  g_object_unref (tag);

  tag = gd_tagged_entry_tag_new ("Blah3");
  gd_tagged_entry_tag_set_has_close_button (tag, FALSE);
  gd_tagged_entry_insert_tag (GD_TAGGED_ENTRY (entry), tag, 0);
  g_object_unref (tag);

  toggle_visible_button = gtk_toggle_button_new_with_label ("Visible");
  gtk_widget_set_vexpand (toggle_visible_button, TRUE);
  gtk_widget_set_valign (toggle_visible_button, GTK_ALIGN_END);
  gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (toggle_visible_button), TRUE);
  g_signal_connect (toggle_visible_button, "toggled",
                    G_CALLBACK (on_toggle_visible), entry);
  gtk_container_add (GTK_CONTAINER (box), toggle_visible_button);

  toggle_tag = gd_tagged_entry_tag_new ("Toggle Tag");

  toggle_tag_button = gtk_toggle_button_new_with_label ("Toggle Tag");
  g_signal_connect (toggle_tag_button, "toggled",
                    G_CALLBACK (on_toggle_tag), entry);
  gtk_container_add (GTK_CONTAINER (box), toggle_tag_button);

  gtk_widget_show_all (window);
  gtk_main ();

  gtk_widget_destroy (window);

  return 0;
}
