// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Shapes

// One of the three Bauhaus forms: "circle", "square" or "triangle".
// Used for the logo, card corners and decorative compositions.
Item {
    id: geo
    property string kind: "square"
    property color color: Theme.red
    property color outline: "transparent"
    property real outlineWidth: 0
    property real size: 10
    width: size; height: size
    implicitWidth: size; implicitHeight: size
    Rectangle {
        visible: geo.kind !== "triangle"; anchors.fill: parent
        radius: geo.kind === "circle" ? width/2 : 0
        color: geo.color; border.color: geo.outline; border.width: geo.outlineWidth
    }
    Shape {
        visible: geo.kind === "triangle"; anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            fillColor: geo.color; strokeColor: geo.outlineWidth > 0 ? geo.outline : "transparent"; strokeWidth: geo.outlineWidth
            joinStyle: ShapePath.MiterJoin
            startX: geo.width/2; startY: 0
            PathLine { x: geo.width; y: geo.height }
            PathLine { x: 0; y: geo.height }
            PathLine { x: geo.width/2; y: 0 }
        }
    }
}
