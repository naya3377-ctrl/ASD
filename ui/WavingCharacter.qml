// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick

// The character says hello: a little hop, the right forearm swings up from the
// elbow and waves three times while the body sways with it, then it settles.
// The figure is two layers cut at the elbow by scripts/make_character.py;
// the elbow's place below is the one that script prints. It plays whenever
// it comes into view and again when clicked.
Item {
    id: character
    property bool playOnShow: true
    readonly property real ratio: body.sourceSize.width > 0 ? body.sourceSize.height / body.sourceSize.width : 1.276
    readonly property real elbowX: .7569 * width
    readonly property real elbowY: .6167 * height
    property real armAngle: 0    // degrees clockwise; negative lifts the forearm
    property real hop: 0         // share of the height
    property real lean: 0        // degrees, about the feet
    readonly property bool playing: waving.running
    implicitWidth: 240; implicitHeight: implicitWidth * ratio
    function wave() { waving.restart(); }

    Item {
        id: figure; width: character.width; height: character.height
        transform: [
            Rotation { origin.x: figure.width/2; origin.y: figure.height; angle: character.lean },
            Translate { y: -character.hop * character.height }
        ]
        Image { id: body; objectName: "characterBody"; anchors.fill: parent; source: "../assets/character/wave-body.png"; smooth: true; mipmap: true }
        Image {
            objectName: "characterForearm"; anchors.fill: parent; source: "../assets/character/wave-forearm.png"; smooth: true; mipmap: true
            transform: Rotation { origin.x: character.elbowX; origin.y: character.elbowY; angle: character.armAngle }
        }
    }
    TapHandler { onTapped: character.wave() }
    HoverHandler { cursorShape: Qt.PointingHandCursor }

    SequentialAnimation {
        id: waving
        // Hop up while the forearm rises.
        ParallelAnimation {
            SequentialAnimation {
                NumberAnimation { target: character; property: "hop"; from: 0; to: .045; duration: 200; easing.type: Easing.OutQuad }
                NumberAnimation { target: character; property: "hop"; to: 0; duration: 380; easing.type: Easing.OutBounce }
            }
            NumberAnimation { target: character; property: "armAngle"; from: 0; to: -86; duration: 460; easing.type: Easing.OutBack }
        }
        // Three waves; the body leans a touch into each.
        SequentialAnimation {
            loops: 3
            ParallelAnimation {
                NumberAnimation { target: character; property: "armAngle"; to: -110; duration: 240; easing.type: Easing.InOutSine }
                NumberAnimation { target: character; property: "lean"; to: -1.6; duration: 240; easing.type: Easing.InOutSine }
            }
            ParallelAnimation {
                NumberAnimation { target: character; property: "armAngle"; to: -70; duration: 240; easing.type: Easing.InOutSine }
                NumberAnimation { target: character; property: "lean"; to: 1.4; duration: 240; easing.type: Easing.InOutSine }
            }
        }
        // Settle back.
        ParallelAnimation {
            NumberAnimation { target: character; property: "armAngle"; to: 0; duration: 520; easing.type: Easing.InOutCubic }
            NumberAnimation { target: character; property: "lean"; to: 0; duration: 520; easing.type: Easing.OutCubic }
        }
    }
    onVisibleChanged: if (visible && playOnShow) waving.restart()
    Component.onCompleted: if (visible && playOnShow) waving.start()
}
