pragma Singleton
import QtQuick

/*!
    Every element the layout can be faulted on, and what has been done to it.

    The sibling of \l TextSizes, and the same arrangement: one row per element
    here beside the artwork, the state itself owned by Python
    (backend/layout.py) so it survives a restart, and Main.qml pushing one into
    the other.

    An element is listed here only if something is watching for it. The point
    is to be able to draw the cluster *wrong* by an exact amount, so that a
    camera-based layout check can be shown to report the displacement that was
    actually applied — on a cluster that is already correct, a validator that
    always answered PASS would score full marks.

    Offsets are in design-canvas pixels, the same units as the coordinates in
    \l Theme and \l BmwTheme, so a commanded 3 px is 3 px of the framebuffer
    whatever the window has been scaled to.
*/
QtObject {
    id: roles

    /*!
        The catalogue.

        \c id is the stable key a fault is stored under — renaming one silently
        drops whatever was set for it. \c group and \c label are what the
        layout panel lists the row as, and \c note says which thing on screen
        it is, since "gauge" describes four of them.
    */
    readonly property var items: [
        // ------------------------------------------------------ classic dials
        { id: "classic.dial.speed", skin: "classic", group: qsTr("Dials"),
          label: qsTr("Speedometer"), note: qsTr("the whole left dial, face and needle") },
        { id: "classic.dial.rpm", skin: "classic", group: qsTr("Dials"),
          label: qsTr("Rev counter"), note: qsTr("the whole right dial") },
        { id: "classic.gauge.fuel", skin: "classic", group: qsTr("Dials"),
          label: qsTr("Fuel arc"), note: qsTr("the segmented arc under the left dial") },
        { id: "classic.gauge.coolant", skin: "classic", group: qsTr("Dials"),
          label: qsTr("Coolant arc"), note: qsTr("the segmented arc under the right dial") },

        // ----------------------------------------------------- classic centre
        { id: "classic.centre", skin: "classic", group: qsTr("Centre column"),
          label: qsTr("Centre column"), note: qsTr("gear, range, trip rows and eco bar") },
        { id: "classic.lane", skin: "classic", group: qsTr("Centre column"),
          label: qsTr("Lane graphic"), note: qsTr("the perspective lane markings") },
        { id: "classic.cruise", skin: "classic", group: qsTr("Centre column"),
          label: qsTr("Cruise set speed"), note: qsTr("bottom left; needs cruise on") },
        { id: "classic.shiftprompt", skin: "classic", group: qsTr("Centre column"),
          label: qsTr("Shift-up prompt"), note: qsTr("the arrow near the redline") },

        // ----------------------------------------------------- classic bottom
        { id: "classic.telltales", skin: "classic", group: qsTr("Strips"),
          label: qsTr("Telltale strip"), note: qsTr("the warning lamp row") },
        { id: "classic.bottombar", skin: "classic", group: qsTr("Strips"),
          label: qsTr("Bottom bar"), note: qsTr("outside temperature and odometer") },

        // --------------------------------------------------------- bmw gauges
        { id: "bmw.gauge.speed", skin: "bmw", group: qsTr("Gauges"),
          label: qsTr("Speed band"), note: qsTr("the left chevron gauge") },
        { id: "bmw.gauge.power", skin: "bmw", group: qsTr("Gauges"),
          label: qsTr("ePower band"), note: qsTr("the right chevron gauge") },

        // -------------------------------------------------------- bmw readout
        { id: "bmw.speed.value", skin: "bmw", group: qsTr("Readouts"),
          label: qsTr("Speed digits"), note: qsTr("far left") },
        { id: "bmw.speed.unit", skin: "bmw", group: qsTr("Readouts"),
          label: qsTr("Speed unit"), note: qsTr("km/h under the digits") },
        { id: "bmw.gear", skin: "bmw", group: qsTr("Readouts"),
          label: qsTr("Gear letter"), note: qsTr("far right, with the ratio under it") },
        { id: "bmw.cruise", skin: "bmw", group: qsTr("Readouts"),
          label: qsTr("Cruise set speed"), note: qsTr("under the speed; needs cruise on") },

        // --------------------------------------------------------- bmw centre
        { id: "bmw.media", skin: "bmw", group: qsTr("Centre"),
          label: qsTr("Media tile"), note: qsTr("cover art, track and progress") },
        { id: "bmw.message", skin: "bmw", group: qsTr("Centre"),
          label: qsTr("Driver message"), note: qsTr("replaces the cover art when set") },

        // --------------------------------------------------------- bmw strips
        { id: "bmw.telltales", skin: "bmw", group: qsTr("Strips"),
          label: qsTr("Telltale strip"), note: qsTr("the warning lamp row") },
        { id: "bmw.statusbar", skin: "bmw", group: qsTr("Strips"),
          label: qsTr("Status strip"), note: qsTr("charge, clock, mode, temperature, range") }
    ]

    // ------------------------------------------------------------------ state
    /*!
        Master switch, pushed in from Python.

        Lets a set of faults be taken out and put back without losing it, which
        is what an A/B capture against the same reference needs.
    */
    property bool enabled: true

    /*! Per-id {dx, dy, scale, rot, hidden}; absent means the element is correct. */
    property var faults: ({})

    readonly property var neutral: ({ dx: 0, dy: 0, scale: 1, rot: 0, hidden: false })

    // ----------------------------------------------------------------- lookup
    /*!
        What has been done to \a id, or \l neutral if nothing has.

        Reading \l faults and \l enabled here is what makes every
        \c LayoutShift a live binding: QML records the dependency through the
        call, so commanding a fault moves the element immediately.
    */
    function faultOf(id) {
        if (!enabled)
            return neutral
        var entry = faults[id]
        if (entry === undefined || entry === null)
            return neutral
        return entry
    }

    function dx(id) { var f = faultOf(id); return f.dx === undefined ? 0 : f.dx }
    function dy(id) { var f = faultOf(id); return f.dy === undefined ? 0 : f.dy }
    function scaleOf(id) { var f = faultOf(id); return f.scale === undefined ? 1 : f.scale }
    function rotOf(id) { var f = faultOf(id); return f.rot === undefined ? 0 : f.rot }
    function isHidden(id) { var f = faultOf(id); return f.hidden === true }

    /*! Whether \a id is displaced right now, for the panel's marker. */
    function isFaulted(id) {
        var f = faultOf(id)
        return f.dx !== 0 || f.dy !== 0 || f.scale !== 1 || f.rot !== 0 || f.hidden === true
    }

    /*! Whether \a id has a fault stored, even with \l enabled off. */
    function hasStoredFault(id) {
        var entry = faults[id]
        return entry !== undefined && entry !== null
    }

    /*! The catalogue row for \a id, for a panel that has only the key. */
    function describe(id) {
        for (var i = 0; i < items.length; ++i)
            if (items[i].id === id)
                return items[i]
        return null
    }
}
