// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick

// A soft shadow under `target`, drawn from a nine-slice image made by
// scripts/make_shadows.py (the numbers in LEVELS match it). Declare it
// before the target so it sits underneath.
BorderImage {
    id: shadow
    required property Item target
    property string level: "small"   // small, medium, large, page
    readonly property var levels: ({small: [8, 6, 1], medium: [16, 10, 3], large: [36, 12, 12], page: [14, 0, 2]})
    readonly property int margin: levels[level][0]
    readonly property int edge: levels[level][0] + levels[level][1]
    readonly property int drop: levels[level][2]
    x: target.x - margin; y: target.y - margin + drop
    width: target.width + 2*margin; height: target.height + 2*margin
    visible: target.visible && target.opacity > 0
    border { left: edge; right: edge; top: edge; bottom: edge }
    source: "../assets/ui/shadow-" + level + ".png"
    smooth: true
}
