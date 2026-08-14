pragma Singleton
import QtQuick

/*! Unit conversion and display formatting shared by the cluster and panel. */
QtObject {
    readonly property real kmToMi: 0.621371
    readonly property real kmlToMpg: 2.35215

    function isImperial(units) { return units === "imperial" }

    // ------------------------------------------------------------- distance
    function speedValue(kmh, units) {
        return Math.round(isImperial(units) ? kmh * kmToMi : kmh)
    }

    function speedUnit(units) { return isImperial(units) ? "mph" : "km/h" }

    function distanceValue(km, units, digits) {
        var v = isImperial(units) ? km * kmToMi : km
        return v.toFixed(digits === undefined ? 1 : digits)
    }

    function distanceUnit(units) { return isImperial(units) ? "mi" : "km" }

    // ------------------------------------------------------------------ rpm
    function rpmValue(rpm) { return (rpm / 1000).toFixed(1) }

    // ------------------------------------------------------------ fuel used
    /*!
        Returns the economy reading for \a kml, honouring \a mode which is one
        of "km/L", "L/100km" or "mpg".  A zero reading renders as blanks, the
        way a trip computer shows an unavailable average.
    */
    function consumptionValue(kml, mode) {
        if (kml <= 0.05)
            return mode === "L/100km" ? "--.-" : "--.-"
        if (mode === "L/100km")
            return (100 / kml).toFixed(1)
        if (mode === "mpg")
            return (kml * kmlToMpg).toFixed(1)
        return kml.toFixed(1)
    }

    function consumptionUnit(mode, units) {
        if (mode === "L/100km") return "L/100km"
        if (mode === "mpg") return "mpg"
        return "km/L"
    }

    // ----------------------------------------------------------------- time
    function duration(totalSeconds) {
        var h = Math.floor(totalSeconds / 3600)
        var m = Math.floor((totalSeconds % 3600) / 60)
        return h + ":" + (m < 10 ? "0" + m : String(m))
    }

    // ---------------------------------------------------------- temperature
    function tempValue(celsius, units) {
        return Math.round(isImperial(units) ? celsius * 9 / 5 + 32 : celsius)
    }

    function tempUnit(units) { return isImperial(units) ? "°F" : "°C" }
}
