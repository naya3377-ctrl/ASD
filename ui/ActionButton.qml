// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls

// Every button in the app. Flat faces and hairline edges, no gloss:
//  - ghost (default): a toolbar button; a faint tint on hover, the quiet
//    blue-grey selection with a blue icon when `active` (the tool in use)
//  - primary: the one main action, filled with the accent
//  - outlined: a secondary push button, white with a hairline edge
//  - tab: a segment of a Segmented control (the control draws the chosen pill)
//  - hud: a button on dark floating controls (slide show, focus reading)
// The click area is at least 32 × 32 and never moves. On press only the
// content shrinks a touch (1 → .97 in 70 ms, back in 140 ms); the command
// itself runs at once.
Button {
    id: control
    property bool active: false
    property bool primary: false
    property bool outlined: false
    property bool tab: false
    property bool hud: false
    property bool leftAligned: false
    property bool compact: false
    property string glyph: ""
    property string hint: ""
    property string shortcutText: ""
    property real iconSize: 18
    readonly property color fillColor: primary ? (down ? Theme.accentPressed : hovered ? Theme.accentHover : Theme.accent)
        : outlined ? (down ? Theme.pressed : hovered ? Theme.hover : "transparent")
        : tab ? (hovered && !active ? Theme.hover : "transparent")
        : hud ? (down ? "#40ffffff" : hovered ? "#26ffffff" : active ? "#33ffffff" : "transparent")
        : active ? Theme.accentSoft : down ? Theme.pressed : hovered ? Theme.hover : "transparent"
    readonly property color baseTone: primary ? Theme.inkOnAccent : hud ? Theme.hudInk : tab ? Theme.inkSoft : Theme.ink
    readonly property color activeTone: primary || hud ? baseTone : tab ? Theme.ink : Theme.accent
    // 0 → 1 as the button becomes active; the icon cross-fades between tones.
    property real activeMix: active ? 1 : 0
    Behavior on activeMix { NumberAnimation { duration: Theme.selectMs; easing.type: Easing.OutCubic } }
    readonly property color tone: active ? activeTone : baseTone

    implicitHeight: Theme.control
    implicitWidth: Math.max(implicitHeight, contentItem.implicitWidth + leftPadding + rightPadding)
    leftPadding: text.length ? (compact ? 10 : 12) : 7; rightPadding: leftPadding
    font.family: Theme.family
    font.pixelSize: Theme.body
    font.weight: primary || (tab && active) || (active && !tab && !hud) ? Font.DemiBold : Font.Medium
    hoverEnabled: true
    focusPolicy: Qt.TabFocus
    opacity: enabled ? 1 : .38

    // Press feedback on the content only, continuing from wherever it is.
    property real press: 1
    NumberAnimation { id: pressMotion; target: control; property: "press"; easing.type: Easing.OutCubic }
    onDownChanged: {
        pressMotion.stop();
        pressMotion.to = down ? Theme.pressScale : 1;
        pressMotion.duration = down ? Theme.pressInMs : Theme.pressOutMs;
        if (Theme.reduceMotion) press = pressMotion.to; else pressMotion.start();
    }

    contentItem: Item {
        implicitWidth: contentRow.implicitWidth; implicitHeight: 20
        Row {
            id: contentRow; spacing: 7; anchors.verticalCenter: parent.verticalCenter
            x: control.leftAligned ? 0 : (parent.width-width)/2
            scale: control.press
            Item {
                width: control.glyph.length ? control.iconSize : 0; height: control.iconSize
                anchors.verticalCenter: parent.verticalCenter; visible: control.glyph.length > 0
                Icon { name: control.glyph; tone: control.baseTone; size: control.iconSize; opacity: 1 - control.activeMix; visible: opacity > 0 }
                Icon { name: control.glyph; tone: control.activeTone; size: control.iconSize; opacity: control.activeMix; visible: opacity > 0 }
            }
            Text {
                visible: control.text.length>0; text: control.text; font: control.font
                color: control.tone; anchors.verticalCenter: parent.verticalCenter
                Behavior on color { ColorAnimation { duration: Theme.selectMs; easing.type: Easing.OutCubic } }
            }
            Text {
                visible: control.shortcutText.length>0 && control.leftAligned; text: control.shortcutText
                font.family: Theme.family; font.pixelSize: Theme.caption; color: Theme.inkMuted
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }
    background: Item {
        Rectangle {
            id: face; anchors.fill: parent
            radius: Theme.radius
            color: control.fillColor
            border.width: control.outlined ? Theme.hairline : 0
            border.color: control.hovered ? Theme.lineStrong : Theme.line
            Behavior on color { ColorAnimation { duration: Theme.hoverMs; easing.type: Easing.OutCubic } }
        }
        // Keyboard focus: a ring just outside the button.
        Rectangle {
            visible: control.visualFocus; anchors.fill: parent; anchors.margins: -2
            radius: Theme.radius+2; color: "transparent"; border.color: Theme.focusRing; border.width: 2
        }
    }
    ToolTip.visible: hovered && hint.length>0
    ToolTip.text: hint; ToolTip.delay: 600
}
