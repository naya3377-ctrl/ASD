// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

FocusScope {
    id: view
    objectName: "presentationView"
    required property var controller
    property int page: controller.currentPage
    property real ratio: controller.pageRatio(page)
    property string pageImage: ""
    property string renderError: ""
    property var requested: []
    property bool controlsVisible: true
    property real wheelRemainder: 0
    property var hoverLink: null
    signal pageRequested(int page)
    signal exitRequested()

    function showControls() { controlsVisible=true; hideControls.restart(); }
    function move(amount) {
        pageRequested(Math.max(0,Math.min(controller.document.count-1,page+amount)));
        forceActiveFocus();
    }
    function refreshImage() {
        pageImage=controller.imageUrl(page,"presentation") || controller.imageUrl(page,"main");
        renderError=controller.imageError(page,"presentation");
    }
    function request() {
        if(!visible || controller.document.count<1) return;
        ratio=controller.pageRatio(page);
        refreshImage();
        var wanted=[page];
        if(page+1<controller.document.count) wanted.push(page+1);
        if(page>0) wanted.push(page-1);
        for(var i=0;i<requested.length;++i)
            if(wanted.indexOf(requested[i])<0) controller.releasePage(requested[i],"presentation");
        requested=wanted;
        for(var n=0;n<wanted.length;++n) {
            var p=wanted[n], r=controller.pageRatio(p);
            var width=Math.max(128,Math.min(view.width-36,(view.height-36)/r));
            controller.requestPage(p,"presentation",Math.ceil(width*Screen.devicePixelRatio));
        }
        controller.requestText(page);
    }
    function linkAt(x,y) {
        var local=surface.mapToItem(paper,x,y);
        if(local.x<0 || local.y<0 || local.x>paper.width || local.y>paper.height) return null;
        var scale=controller.pageWidth(page)/paper.width;
        var links=controller.textLayout(page).links || [];
        for(var i=0;i<links.length;++i) {
            var r=links[i].rect;
            if(local.x*scale>=r[0] && local.x*scale<=r[2] && local.y*scale>=r[1] && local.y*scale<=r[3]) return links[i];
        }
        return null;
    }
    onPageChanged: { hoverLink=null; request(); }
    onWidthChanged: renderDelay.restart()
    onHeightChanged: renderDelay.restart()
    Component.onCompleted: { request(); showControls(); }
    Component.onDestruction: { for(var i=0;i<requested.length;++i) controller.releasePage(requested[i],"presentation"); }
    Connections {
        target: view.controller
        function onStateChanged() { view.request(); }
        function onPageImageChanged(page,kind) { if(page===view.page && (kind==="presentation" || kind==="main")) view.refreshImage(); }
        function onPageMetricsChanged(page) { if(page===view.page) { view.ratio=view.controller.pageRatio(page); renderDelay.restart(); } }
    }
    Timer { id: renderDelay; interval: 80; onTriggered: view.request() }
    Timer { id: hideControls; interval: 2400; onTriggered: { if(!controlsHover.hovered) view.controlsVisible=false; else restart(); } }

    Rectangle { anchors.fill: parent; color: Theme.black }
    Rectangle {
        id: paper; objectName: "presentationPaper"; anchors.centerIn: parent
        width: Math.max(1,Math.min(view.width-36,(view.height-36)/view.ratio)); height: width*view.ratio
        color: "white"
        Image {
            objectName: "presentationImage"; anchors.fill: parent
            source: view.pageImage; fillMode: Image.Stretch; cache: false; asynchronous: true
            retainWhileLoading: false; smooth: true
        }
        Text {
            anchors.centerIn: parent; visible: !view.pageImage
            text: view.renderError ? "페이지를 표시하지 못했어요." : "페이지 불러오는 중…"
            color: "#8a7f73"; font.pixelSize: 14
        }
    }
    MouseArea {
        id: surface; objectName: "presentationSurface"; anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.RightButton; hoverEnabled: true
        cursorShape: !view.controlsVisible ? Qt.BlankCursor : view.hoverLink ? Qt.PointingHandCursor : Qt.ArrowCursor
        onPositionChanged: function(mouse) { view.showControls(); view.hoverLink=view.linkAt(mouse.x,mouse.y); }
        onClicked: function(mouse) {
            var link=view.linkAt(mouse.x,mouse.y);
            if(mouse.button===Qt.RightButton) view.move(-1);
            else if(link) view.controller.activateLink(link);
            else view.move(1);
        }
        onWheel: function(wheel) {
            if(!(wheel.modifiers & Qt.ControlModifier)) {
                var delta=wheel.pixelDelta.y ? wheel.pixelDelta.y/80 : wheel.angleDelta.y/120;
                view.wheelRemainder-=delta;
                var steps=view.wheelRemainder>0 ? Math.floor(view.wheelRemainder) : Math.ceil(view.wheelRemainder);
                if(steps) { view.wheelRemainder-=steps; view.move(steps); }
            }
            wheel.accepted=true;
        }
    }
    ActionButton {
        anchors.centerIn: parent; anchors.verticalCenterOffset: 40
        visible: !view.pageImage && !!view.renderError; text: "다시 불러오기"; outlined: true
        onClicked: view.controller.retryPage(view.page,"presentation",Math.ceil(paper.width*Screen.devicePixelRatio))
    }
    Rectangle {
        anchors.top: parent.top; anchors.horizontalCenter: parent.horizontalCenter; anchors.topMargin: 12
        width: Math.min(parent.width-36,title.implicitWidth+30); height: 30
        radius: height/2; color: Theme.hud; visible: view.controlsVisible
        Text { id: title; anchors.fill: parent; anchors.leftMargin: 15; anchors.rightMargin: 15; verticalAlignment: Text.AlignVCenter; text: "윤DF · "+view.controller.document.name; elide: Text.ElideMiddle; font.pixelSize: Theme.small; color: Theme.hudInk }
    }
    Rectangle {
        id: controls; objectName: "presentationControls"
        anchors.bottom: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter; anchors.bottomMargin: 14
        width: toolbar.implicitWidth+24; height: 54
        visible: view.controlsVisible; color: Theme.hud; radius: Theme.radiusLarge+3
        HoverHandler { id: controlsHover }
        RowLayout {
            id: toolbar; anchors.centerIn: parent; spacing: 8
            ActionButton { objectName: "slidePreviousButton"; glyph: "left"; hud: true; enabled: view.page>0; hint: "이전 페이지 · ← / ↑ / Page Up"; onClicked: { view.move(-1); view.showControls(); } }
            Text { objectName: "slidePageNumber"; text: (view.page+1)+" / "+view.controller.document.count; horizontalAlignment: Text.AlignHCenter; Layout.minimumWidth: 76; color: Theme.hudInk; font.features: ({ "tnum": 1 }); font.pixelSize: Theme.body; font.weight: Font.DemiBold }
            ActionButton { objectName: "slideNextButton"; glyph: "right"; hud: true; enabled: view.page<view.controller.document.count-1; hint: "다음 페이지 · → / ↓ / Page Down / Space"; onClicked: { view.move(1); view.showControls(); } }
            Rectangle { width: Theme.hairline; height: 22; color: "#33ffffff" }
            ActionButton { objectName: "exitPresentationButton"; text: "종료 · Esc"; primary: true; onClicked: view.exitRequested() }
        }
    }
}
