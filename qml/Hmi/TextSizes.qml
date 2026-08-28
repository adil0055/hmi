pragma Singleton
import QtQuick

/*!
    Every run of text the cluster draws, and how big it is set.

    The typeface is switchable at runtime, so its size had to become
    switchable too — a face picked for its numerals is often the wrong size
    for the captions around them, and the only way to find out is to try it.
    This is where that lives: one row per text run, with the size the artwork
    was drawn at (\c base), an optional user override, and a global \l scale
    over the lot.

    \l Theme and \l BmwTheme expose these as the size properties they always
    had, so the drawing code is unchanged and still reads \c Theme.gearSize —
    the difference is that those are now bindings, so nudging a size here
    reflows the cluster immediately.

    Sizes are *design* sizes, quoted against the reference face, exactly as
    \l Theme.px expects: what finally reaches \c font.pixelSize is
    \c Theme.px(TextSizes.size(id)), which is this number adjusted for how
    tall the loaded face draws its capitals.

    The state is owned by Python (backend/sizes.py) so it survives a restart;
    Main.qml pushes it in here the same way it pushes the typeface into Theme.
*/
QtObject {
    id: sizes

    /*!
        The catalogue.

        \c id is the stable key overrides are stored under — renaming one
        silently drops whatever the user had set for it. \c group and \c label
        are what the size panel lists the row as, and \c note says which text
        on screen it actually is, since "unit" alone describes four of them.
    */
    readonly property var roles: [
        // ------------------------------------------------------- classic dials
        { id: "classic.dial.speed", skin: "classic", group: qsTr("Dials"),
          label: qsTr("Speed digits"), note: qsTr("centre of the left dial"), base: 96 },
        { id: "classic.dial.rpm", skin: "classic", group: qsTr("Dials"),
          label: qsTr("Rev counter digits"), note: qsTr("centre of the right dial"), base: 88 },
        { id: "classic.dial.unit", skin: "classic", group: qsTr("Dials"),
          label: qsTr("Dial caption"), note: qsTr("km/h and x1000, under each readout"), base: 23 },
        { id: "classic.dial.label", skin: "classic", group: qsTr("Dials"),
          label: qsTr("Scale numerals"), note: qsTr("the numbers around both rings"), base: 34 },
        { id: "classic.mini.label", skin: "classic", group: qsTr("Dials"),
          label: qsTr("Fuel and temperature letters"), note: qsTr("E / F and C / H"), base: 24 },

        // ------------------------------------------------------ classic centre
        { id: "classic.gear", skin: "classic", group: qsTr("Centre column"),
          label: qsTr("Gear letter"), note: qsTr("P R N D, top of the centre column"), base: 72 },
        { id: "classic.gear.number", skin: "classic", group: qsTr("Centre column"),
          label: qsTr("Gear number"), note: qsTr("the ratio beside the letter, in D"), base: 40 },
        { id: "classic.range.value", skin: "classic", group: qsTr("Centre column"),
          label: qsTr("Range figure"), note: qsTr("beside the pump icon"), base: 54 },
        { id: "classic.range.unit", skin: "classic", group: qsTr("Centre column"),
          label: qsTr("Range unit"), note: qsTr("km after the range figure"), base: 24 },
        { id: "classic.driveinfo", skin: "classic", group: qsTr("Centre column"),
          label: qsTr("Drive info heading"), note: qsTr("over the trip rows"), base: 31 },
        { id: "classic.info.label", skin: "classic", group: qsTr("Centre column"),
          label: qsTr("Trip labels"), note: qsTr("Trip / Timer / Avg."), base: 28 },
        { id: "classic.info.value", skin: "classic", group: qsTr("Centre column"),
          label: qsTr("Trip figures"), note: qsTr("the three right-aligned readouts"), base: 36 },
        { id: "classic.info.unit", skin: "classic", group: qsTr("Centre column"),
          label: qsTr("Trip units"), note: qsTr("km, h and l/100km"), base: 21 },
        { id: "classic.eco.scale", skin: "classic", group: qsTr("Centre column"),
          label: qsTr("Eco bar scale"), note: qsTr("0 10 20 30 under the bar"), base: 20 },
        { id: "classic.message", skin: "classic", group: qsTr("Centre column"),
          label: qsTr("Driver message"), note: qsTr("the amber line under the eco bar"), base: 22 },

        // ------------------------------------------------------ classic bottom
        { id: "classic.bottom.value", skin: "classic", group: qsTr("Bottom panel"),
          label: qsTr("Temperature and odometer"), note: qsTr("the two stacked figures"), base: 34 },
        { id: "classic.bottom.unit", skin: "classic", group: qsTr("Bottom panel"),
          label: qsTr("Temperature and odometer units"), note: qsTr("the two unit captions"), base: 20 },
        { id: "classic.cruise.value", skin: "classic", group: qsTr("Bottom panel"),
          label: qsTr("Cruise set speed"), note: qsTr("left of the bottom panel"), base: 40 },
        { id: "classic.cruise.unit", skin: "classic", group: qsTr("Bottom panel"),
          label: qsTr("Cruise unit"), note: qsTr("km/h after the set speed"), base: 19 },
        // `ui` marks the one run that is not set in the cluster's typeface, so
        // the panel does not offer it a preview in a face it will never use.
        { id: "classic.shift", skin: "classic", group: qsTr("Bottom panel"),
          label: qsTr("Shift-up prompt"), note: qsTr("the arrow by the redline, in the UI face"),
          base: 34, ui: true },

        // ---------------------------------------------------------- bmw gauges
        { id: "bmw.scale.label", skin: "bmw", group: qsTr("Chevron gauges"),
          label: qsTr("Scale numerals"), note: qsTr("inside each chevron band"), base: 21 },
        { id: "bmw.gauge.caption", skin: "bmw", group: qsTr("Chevron gauges"),
          label: qsTr("Gauge caption"), note: qsTr("km/h and ePower, above the bands"), base: 20 },

        // -------------------------------------------------------- bmw readouts
        { id: "bmw.speed.value", skin: "bmw", group: qsTr("Readouts"),
          label: qsTr("Speed digits"), note: qsTr("far left"), base: 116 },
        { id: "bmw.speed.unit", skin: "bmw", group: qsTr("Readouts"),
          label: qsTr("Speed unit"), note: qsTr("under the speed"), base: 26 },
        { id: "bmw.gear", skin: "bmw", group: qsTr("Readouts"),
          label: qsTr("Gear letter"), note: qsTr("far right"), base: 108 },
        { id: "bmw.gear.number", skin: "bmw", group: qsTr("Readouts"),
          label: qsTr("Gear number"), note: qsTr("under the letter, in D"), base: 30 },
        { id: "bmw.cruise.value", skin: "bmw", group: qsTr("Readouts"),
          label: qsTr("Cruise set speed"), note: qsTr("under the speed unit"), base: 30 },
        { id: "bmw.cruise.unit", skin: "bmw", group: qsTr("Readouts"),
          label: qsTr("Cruise unit"), note: qsTr("after the set speed"), base: 16 },
        { id: "bmw.message", skin: "bmw", group: qsTr("Readouts"),
          label: qsTr("Driver message"), note: qsTr("the amber banner over the centre"), base: 21 },

        // --------------------------------------------------- bmw centre stack
        { id: "bmw.track.title", skin: "bmw", group: qsTr("Media tile"),
          label: qsTr("Track title"), note: qsTr("under the artwork"), base: 25 },
        { id: "bmw.track.artist", skin: "bmw", group: qsTr("Media tile"),
          label: qsTr("Track artist"), note: qsTr("under the title"), base: 21 },
        { id: "bmw.track.remaining", skin: "bmw", group: qsTr("Media tile"),
          label: qsTr("Time remaining"), note: qsTr("right end of the progress rail"), base: 18 },
        { id: "bmw.track.paused", skin: "bmw", group: qsTr("Media tile"),
          label: qsTr("Paused marker"), note: qsTr("left end of the progress rail"), base: 16 },

        // ------------------------------------------------------ bmw status bar
        { id: "bmw.status.value", skin: "bmw", group: qsTr("Status bar"),
          label: qsTr("Status figures"), note: qsTr("charge, clock, range, outside temp"), base: 22 },
        { id: "bmw.status.mode", skin: "bmw", group: qsTr("Status bar"),
          label: qsTr("Drive mode"), note: qsTr("centred, letterspaced"), base: 18 },
        { id: "bmw.status.unit", skin: "bmw", group: qsTr("Status bar"),
          label: qsTr("Status units"), note: qsTr("after the range and temperature"), base: 17 }
    ]

    // ------------------------------------------------------------------ state
    /*! Multiplies every size at once. Pushed in from Python, which persists it. */
    property real scale: 1.0
    /*! Per-role design sizes, before \l scale; absent means "use the base". */
    property var overrides: ({})

    /*! Base size per id, so a lookup doesn't walk \l roles. Built once. */
    readonly property var baseSizes: {
        var map = {}
        for (var i = 0; i < roles.length; ++i)
            map[roles[i].id] = roles[i].base
        return map
    }

    // ----------------------------------------------------------------- lookup
    /*!
        Design size for \a id, override and scale applied.

        Reading \l overrides and \l scale here is what makes every
        \c Theme.<name>Size a live binding: QML records the dependency through
        the call, so a change to either reflows the cluster.
    */
    function size(id) {
        var value = overrides[id]
        if (value === undefined || value === null)
            value = baseSizes[id]
        // An unknown id is a typo in the artwork rather than user input, so it
        // gets something legible instead of a zero-height run of text.
        return (value === undefined ? 24 : value) * scale
    }

    /*! The size the artwork was drawn at, before override and scale. */
    function baseSize(id) {
        var value = baseSizes[id]
        return value === undefined ? 24 : value
    }

    /*! Whether \a id has been moved off the size it was drawn at. */
    function isOverridden(id) {
        var value = overrides[id]
        return value !== undefined && value !== null
    }
}
