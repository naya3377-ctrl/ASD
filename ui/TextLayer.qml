// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls

Item {
    id: layer
    property var controller: bridge
    property bool allowEdits: true
    property var contextAnnotation: null
    property string markupTool: ""
    property bool menuOpen: contextMenu.visible
    property var comments: controller.pageAnnotations(pageNumber)
    Connections { target: layer.controller; function onAnnotationsChanged(){ layer.comments=layer.controller.pageAnnotations(layer.pageNumber); } }
    property var hoverAnnotation: null
    required property int pageNumber
    required property real pdfWidth
    required property var viewport
    // Hidden layers (editing modes) skip copying the page's character table.
    property var layout: { controller.textTick; return layer.visible ? controller.textLayout(pageNumber) : ({chars: [], lines: [], links: [], images: [], copyable: false, hasText: false}); }
    property var selection: controller.textSelection
    property real factor: width / pdfWidth
    property int anchor: 0
    property var hoverLink: null
    property var contextLink: null
    property var contextImage: null
    property point contextPoint: Qt.point(0,0)
    function imageAt(x,y) {
        var items=layout.images || [];
        for(var i=items.length-1;i>=0;--i) {
            var r=items[i].rect;
            if(x>=r[0] && x<=r[2] && y>=r[1] && y<=r[3]) return items[i];
        }
        return null;
    }
    objectName: "textLayer" + pageNumber
    onLayoutChanged: highlight.requestPaint()
    onSelectionChanged: highlight.requestPaint()
    onWidthChanged: highlight.requestPaint()
    onHeightChanged: highlight.requestPaint()

    function annotationAt(x,y) {
        for(var i=comments.length-1;i>=0;--i) {
            var a=comments[i];
            if(a.reply || (a.flags & 35)) continue;
            for(var n=0;n<a.regions.length;++n) {
                var r=a.regions[n]; if(x>=r[0] && x<=r[2] && y>=r[1] && y<=r[3]) return a;
            }
        }
        return null;
    }
    function linkAt(x, y) {
        var links = layout.links || [];
        for (var i = 0; i < links.length; ++i) {
            var r = links[i].rect;
            if (x >= r[0] && x <= r[2] && y >= r[1] && y <= r[3]) return links[i];
        }
        return null;
    }
    function distance(x, y, r) {
        var dx = Math.max(r[0]-x, 0, x-r[2]);
        var dy = Math.max(r[1]-y, 0, y-r[3]);
        return dx*dx + dy*dy;
    }
    function caretAt(x, y) {
        var lines = layout.lines, chars = layout.chars;
        if (!lines.length) return 0;
        var best = lines[0], score = Infinity;
        for (var n = 0; n < lines.length; ++n) {
            var d = distance(x,y,lines[n].rect);
            if (d < score) { score = d; best = lines[n]; }
        }
        var index = best.start; score = Infinity;
        for (var i = best.start; i < best.end; ++i) {
            var c = chars[i];
            var cd = distance(x,y,[c[1],c[2],c[3],c[4]]);
            if (cd < score) { score = cd; index = i; }
        }
        var ch = chars[index];
        return index + (((x-(ch[1]+ch[3])/2)*best.dx + (y-(ch[2]+ch[4])/2)*best.dy >= 0) ? 1 : 0);
    }
    function selectWord(x, y) {
        var chars = layout.chars;
        if (!chars.length) return;
        var i = Math.min(chars.length-1, caretAt(x,y));
        var a = i, b = i+1, line = chars[i][5];
        while (a > 0 && chars[a-1][5] === line && !/\s/.test(chars[a-1][0])) --a;
        while (b < chars.length && chars[b][5] === line && !/\s/.test(chars[b][0])) ++b;
        anchor = a;
        controller.selectCharacters(pageNumber,a,b);
    }
    Canvas {
        id: highlight; anchors.fill: parent
        // A page-sized canvas costs tens of MB per repaint at high zoom.
        // Only keep it while this page actually has a selection.
        visible: layer.selection.page === layer.pageNumber && layer.selection.end > layer.selection.start
        onVisibleChanged: if(visible) requestPaint()
        onPaint: {
            var ctx = getContext("2d"); ctx.reset();
            if (layer.selection.page !== layer.pageNumber) return;
            var chars = layer.layout.chars;
            var a = layer.selection.start, b = Math.min(chars.length,layer.selection.end);
            ctx.fillStyle = "rgba(53, 119, 232, 0.30)";
            // Per-line unions keep inter-character spaces selected too.
            var rect = null, line = -1;
            function paint() {
                if (rect) ctx.fillRect(rect[0]*layer.factor,rect[1]*layer.factor,
                    (rect[2]-rect[0])*layer.factor,(rect[3]-rect[1])*layer.factor);
            }
            for (var i=a; i<b; ++i) {
                var c = chars[i];
                if (c[5] !== line) { paint(); rect = [c[1],c[2],c[3],c[4]]; line=c[5]; }
                else { rect[0]=Math.min(rect[0],c[1]); rect[1]=Math.min(rect[1],c[2]);
                       rect[2]=Math.max(rect[2],c[3]); rect[3]=Math.max(rect[3],c[4]); }
            }
            paint();
        }
    }
    MouseArea {
        id: pointer; anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        preventStealing: true; hoverEnabled: true
        cursorShape: layer.hoverLink || layer.hoverAnnotation ? Qt.PointingHandCursor : layer.layout.chars.length ? Qt.IBeamCursor : Qt.ArrowCursor
        property point start: Qt.point(0,0)
        property bool moved: false
        property bool doubleClick: false
        property var pressedLink: null
        property var pressedAnnotation: null
        property point notePoint
        property bool draggingNote: moved && pressedAnnotation!==null && pressedAnnotation.type==="Text" && pressedAnnotation.editable && layer.allowEdits
        onPressed: function(mouse) {
            layer.forceActiveFocus();
            controller.setCurrentPage(layer.pageNumber);
            if (mouse.button === Qt.RightButton) {
                layer.contextPoint=Qt.point(mouse.x/layer.factor,mouse.y/layer.factor);
                layer.contextLink=layer.linkAt(layer.contextPoint.x,layer.contextPoint.y);
                layer.contextImage=layer.imageAt(layer.contextPoint.x,layer.contextPoint.y);
                layer.contextAnnotation=layer.annotationAt(layer.contextPoint.x,layer.contextPoint.y);
                contextMenu.popup(); return;
            }
            start = Qt.point(mouse.x,mouse.y); moved = false; doubleClick = false;
            pressedLink = layer.linkAt(mouse.x/layer.factor,mouse.y/layer.factor);
            pressedAnnotation = layer.annotationAt(mouse.x/layer.factor,mouse.y/layer.factor);
            if(pressedAnnotation) notePoint=Qt.point(pressedAnnotation.rect[0],pressedAnnotation.rect[1]);
            var caret = layer.caretAt(mouse.x/layer.factor,mouse.y/layer.factor);
            if (!(mouse.modifiers & Qt.ShiftModifier) || layer.selection.page !== layer.pageNumber) layer.anchor = caret;
            controller.selectCharacters(layer.pageNumber,layer.anchor,caret);
        }
        onPositionChanged: function(mouse) {
            layer.hoverLink = layer.linkAt(mouse.x/layer.factor,mouse.y/layer.factor);
            layer.hoverAnnotation = layer.annotationAt(mouse.x/layer.factor,mouse.y/layer.factor);
            if (pressed && (pressedButtons & Qt.LeftButton)) {
                if (Math.abs(mouse.x-start.x)+Math.abs(mouse.y-start.y)>4) moved=true;
                if(draggingNote) notePoint=Qt.point(pressedAnnotation.rect[0]+(mouse.x-start.x)/layer.factor,pressedAnnotation.rect[1]+(mouse.y-start.y)/layer.factor);
                else if (moved) controller.selectCharacters(layer.pageNumber,layer.anchor,layer.caretAt(mouse.x/layer.factor,mouse.y/layer.factor));
            }
        }
        onReleased: function(mouse) {
            if (mouse.button !== Qt.LeftButton || doubleClick) return;
            if(draggingNote) {controller.moveAnnotation(pressedAnnotation,[notePoint.x,notePoint.y]);moved=false;return;}
            if (moved) {
                controller.selectCharacters(layer.pageNumber,layer.anchor,layer.caretAt(mouse.x/layer.factor,mouse.y/layer.factor));
                if(layer.markupTool && layer.allowEdits) controller.annotateSelection(layer.markupTool);
            }
            // Already on screen: select it and bring its card into view, without scrolling the page.
            else if (pressedAnnotation && !layer.markupTool) controller.focusAnnotation(layer.pageNumber,pressedAnnotation.id);
            else if (pressedLink && layer.linkAt(mouse.x/layer.factor,mouse.y/layer.factor)) controller.activateLink(pressedLink);
        }
        onDoubleClicked: function(mouse) {
            doubleClick=true;
            // Double-clicking a mark opens its memo, as in Acrobat.
            if (pressedAnnotation && pressedAnnotation.editable && layer.allowEdits && controller.canAnnotate) { controller.annotateItem(pressedAnnotation); return; }
            if (!pressedLink) layer.selectWord(mouse.x/layer.factor,mouse.y/layer.factor);
        }
        onExited: { layer.hoverLink=null; layer.hoverAnnotation=null; }
        // Links show their target; comment marks show who wrote what, next to the pointer.
        ToolTip {
            id: pointerTip
            x: Math.min(pointer.mouseX + 14, pointer.width - width); y: pointer.mouseY + 20
            delay: 450; font.pixelSize: 12
            visible: pointer.containsMouse && !pointer.pressed && text.length > 0
            text: layer.hoverLink ? (layer.hoverLink.kind === "uri" ? layer.hoverLink.uri : layer.hoverLink.kind === "page" ? (layer.hoverLink.page+1)+"페이지로 이동" : "문서 링크")
                : !layer.hoverAnnotation || !(layer.hoverAnnotation.content || layer.hoverAnnotation.author) ? ""
                : (layer.hoverAnnotation.author ? layer.hoverAnnotation.author + " · " : "") + (layer.hoverAnnotation.content || layer.hoverAnnotation.label).slice(0,160)
        }
    }
    Rectangle {
        visible: pointer.pressed && pointer.draggingNote
        x: pointer.notePoint.x*layer.factor; y: pointer.notePoint.y*layer.factor
        width: pointer.pressedAnnotation ? (pointer.pressedAnnotation.rect[2]-pointer.pressedAnnotation.rect[0])*layer.factor : 0
        height: pointer.pressedAnnotation ? (pointer.pressedAnnotation.rect[3]-pointer.pressedAnnotation.rect[1])*layer.factor : 0
        color: "#88ffd54f"; border.color: Theme.accent; border.width: 2; z: 10
    }
    Timer {
        interval: 25; repeat: true; running: pointer.pressed && pointer.moved && !pointer.draggingNote
        onTriggered: {
            var p = pointer.mapToItem(layer.viewport,pointer.mouseX,pointer.mouseY);
            var step = p.y < 24 ? -Math.min(24,24-p.y) : p.y > layer.viewport.height-24 ? Math.min(24,p.y-layer.viewport.height+24) : 0;
            if (!step) return;
            var min = layer.viewport.originY-layer.viewport.topMargin;
            var max = Math.max(min,layer.viewport.originY+layer.viewport.contentHeight-layer.viewport.height+layer.viewport.bottomMargin);
            layer.viewport.contentY = Math.max(min,Math.min(max,layer.viewport.contentY+step));
            var local = layer.viewport.mapToItem(layer,p.x,p.y);
            controller.selectCharacters(layer.pageNumber,layer.anchor,layer.caretAt(local.x/layer.factor,local.y/layer.factor));
        }
    }
    Menu {
        id: contextMenu; objectName: "pageContextMenu"+layer.pageNumber
        MenuItem {
            objectName: "deleteAnnotationMenuItem"
            text: layer.contextAnnotation && layer.contextAnnotation.type==="Highlight" ? "형광펜 삭제" : "주석 삭제"
            visible: layer.contextAnnotation!==null; height: visible ? implicitHeight : 0
            enabled: layer.allowEdits && controller.canAnnotate && !!layer.contextAnnotation && layer.contextAnnotation.editable
            onTriggered: controller.deleteAnnotationAt(layer.contextAnnotation)
        }
        // On a mark the memo belongs to that mark; on selected text it becomes
        // a highlight carrying the memo; elsewhere it is a note at the point.
        MenuItem {
            objectName: "addMemoMenuItem"
            readonly property bool onMark: !!layer.contextAnnotation && layer.contextAnnotation.editable
            text: onMark ? (layer.contextAnnotation.content ? "메모 수정" : "이 표시에 메모 달기")
                : layer.selection.count>0 && layer.selection.page===layer.pageNumber ? "선택한 글자에 메모 달기" : "여기에 메모 추가"
            enabled: layer.allowEdits && controller.canAnnotate
            onTriggered: onMark ? controller.annotateItem(layer.contextAnnotation) : controller.composeComment(layer.pageNumber,layer.contextPoint.x,layer.contextPoint.y)
        }
        MenuSeparator { }
        MenuItem { objectName: "copyImageMenuItem"; text: "이미지 복사"; visible: layer.contextImage!==null; height: visible ? implicitHeight : 0; onTriggered: controller.exportImage(layer.contextImage,false) }
        MenuItem { objectName: "saveImageMenuItem"; text: "이미지를 파일로 저장…"; visible: layer.contextImage!==null; height: visible ? implicitHeight : 0; onTriggered: controller.exportImage(layer.contextImage,true) }
        MenuSeparator { visible: layer.contextImage!==null; height: visible ? implicitHeight : 0 }
        MenuItem { objectName: "highlightMenuItem"; text: "형광펜"; enabled: layer.allowEdits && controller.canAnnotate && controller.textSelection.count>0; onTriggered: controller.annotateSelection("highlight") }
        MenuItem { text: "밑줄"; enabled: layer.allowEdits && controller.canAnnotate && controller.textSelection.count>0; onTriggered: controller.annotateSelection("underline") }
        MenuItem { text: "취소선"; enabled: layer.allowEdits && controller.canAnnotate && controller.textSelection.count>0; onTriggered: controller.annotateSelection("strikeout") }
        MenuSeparator { }
        MenuItem { text: "복사\tCtrl+C"; enabled: controller.textSelection.count>0; onTriggered: controller.copySelection() }
        MenuItem { text: "이 페이지의 텍스트 전체 선택"; enabled: layer.layout.copyable; onTriggered: { controller.setCurrentPage(layer.pageNumber); controller.selectAllText(); } }
        MenuItem { text: "링크 열기"; visible: layer.contextLink !== null; height: visible ? implicitHeight : 0; onTriggered: controller.activateLink(layer.contextLink) }
    }
}
