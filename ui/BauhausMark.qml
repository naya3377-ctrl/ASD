// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick

// The brand: a sheet of paper built from colour blocks. A black frame holds
// a red field above, blue and yellow below, divided by black rules.
// `size` is the height; the sheet keeps a page-like 4:5 proportion.
Rectangle {
    id: mark
    property real size: 20
    readonly property real rule: Math.max(1.5, Math.round(size*.1))
    readonly property real inner: size - 2*rule
    width: Math.round(size*.8); height: size
    implicitWidth: width; implicitHeight: height
    color: Theme.black
    // Red field: the upper 58% of the sheet.
    Rectangle { x: mark.rule; y: mark.rule; width: mark.width-2*mark.rule; height: Math.round(mark.inner*.58); color: Theme.red; id: top }
    // Blue block, lower left.
    Rectangle { x: mark.rule; y: top.y+top.height+mark.rule; width: Math.round((mark.width-3*mark.rule)*.62); height: mark.height-y-mark.rule; color: Theme.blue; id: left }
    // Yellow block, lower right.
    Rectangle { x: left.x+left.width+mark.rule; y: left.y; width: mark.width-x-mark.rule; height: left.height; color: Theme.yellow }
}
