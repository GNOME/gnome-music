namespace Music {
    public string seconds_to_string (int seconds) {
        string length ="";

        int hours = seconds/3600;
        int remaining_seconds = seconds - (hours * 3600);
        int minutes = remaining_seconds / 60;
        remaining_seconds = remaining_seconds - (minutes * 60);

        if (hours > 0) {
            length = _("%02u:%02u:%02u").printf (hours, minutes, remaining_seconds);
        }
        else {
            length = _("%02u:%02u").printf (minutes, remaining_seconds);
        }

        return length;
    }
}
