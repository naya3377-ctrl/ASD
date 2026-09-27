// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick

// The brand: circle, square and triangle in the three primaries.
Row {
    id: mark
    property real size: 14
    spacing: Math.round(size*.22)
    Geo { kind: "circle"; color: Theme.red; size: mark.size }
    Geo { kind: "square"; color: Theme.blue; size: mark.size }
    Geo { kind: "triangle"; color: Theme.yellow; size: mark.size }
}
