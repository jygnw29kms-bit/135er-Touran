package de.growcentral.touranlive;

/**
 * Transport-neutral navigation maneuver for the 135er Touran MFA bridge.
 * This class deliberately has no HERE SDK dependency so the app and ESP32
 * protocol can be built/tested before HERE developer credentials are added.
 */
public final class NavigationManeuver {
    public final boolean active;
    public final String action;
    public final int distanceMeters;
    public final String roadName;
    public final String roadNumber;
    public final String exitText;
    public final int roundaboutExit;
    public final double headingDegrees;

    public NavigationManeuver(boolean active, String action, int distanceMeters,
                              String roadName, String roadNumber, String exitText,
                              int roundaboutExit, double headingDegrees) {
        this.active = active;
        this.action = safe(action);
        this.distanceMeters = Math.max(0, distanceMeters);
        this.roadName = safe(roadName);
        this.roadNumber = safe(roadNumber);
        this.exitText = safe(exitText);
        this.roundaboutExit = Math.max(0, roundaboutExit);
        this.headingDegrees = normalizeHeading(headingDegrees);
    }

    public static NavigationManeuver inactive() {
        return new NavigationManeuver(false, "NONE", 0, "", "", "", 0, 0.0);
    }

    private static double normalizeHeading(double degrees) {
        if (Double.isNaN(degrees) || Double.isInfinite(degrees)) return 0.0;
        double v = degrees % 360.0;
        return v < 0 ? v + 360.0 : v;
    }

    private static String safe(String value) {
        return value == null ? "" : value.trim();
    }
}
