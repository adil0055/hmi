import QtQuick
import Hmi

/*!
    Applies \l LayoutRoles' fault for one element, and nothing else.

    Wrap an element in one of these and it gains a commanded displacement:

    \qml
    LayoutShift {
        role: "classic.dial.speed"
        pivotX: Theme.dialCxLeft; pivotY: Theme.dialCy
        Dial { centreX: Theme.dialCxLeft; ... }
    }
    \endqml

    It fills its parent and carries design-canvas coordinates through
    unchanged, so the element inside keeps positioning itself exactly as it did
    — wrapping one costs a line and changes nothing until a fault is commanded.

    \l pivotX and \l pivotY are the element's own centre, and only matter for
    \c scale and \c rot: without them an element would grow and turn about the
    middle of the canvas, which moves it as well as resizing it and makes the
    commanded value untestable. They default to the centre of the canvas, so
    set them on anything that is not the whole screen.

    Faulted elements are deliberately *not* clipped to their nominal box: an
    element that has been pushed somewhere it should not be is exactly what the
    thing watching the screen is supposed to notice.
*/
Item {
    id: shift

    /*! Key into \l LayoutRoles.items. */
    required property string role

    /*! The element's own centre in design pixels, for scale and rotation. */
    property real pivotX: width / 2
    property real pivotY: height / 2

    width: parent ? parent.width : 0
    height: parent ? parent.height : 0

    x: LayoutRoles.dx(role)
    y: LayoutRoles.dy(role)
    visible: !LayoutRoles.isHidden(role)

    transform: [
        Scale {
            origin.x: shift.pivotX
            origin.y: shift.pivotY
            xScale: LayoutRoles.scaleOf(shift.role)
            yScale: LayoutRoles.scaleOf(shift.role)
        },
        Rotation {
            origin.x: shift.pivotX
            origin.y: shift.pivotY
            angle: LayoutRoles.rotOf(shift.role)
        }
    ]
}
