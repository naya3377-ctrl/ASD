import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: root
    objectName: "mainWindow"
    width: 1320; height: 900
    minimumWidth: presenting ? 0 : 1000; minimumHeight: presenting ? 0 : 640
    visibility: Window.Windowed
    title: root.hasDocument ? (pdf.document.dirty ? "● " : "") + pdf.document.name + " — 윤DF " + Qt.application.version : "윤DF " + Qt.application.version
    color: Theme.canvas
    // Standard controls (dialogs, menus, fields) follow the same palette.
    palette.window: Theme.surface
    palette.windowText: Theme.ink
    palette.base: Theme.field
    palette.alternateBase: Theme.surfaceAlt
    palette.text: Theme.ink
    palette.button: Theme.raised
    palette.buttonText: Theme.ink
    palette.highlight: Theme.accent
    palette.highlightedText: Theme.onAccent
    palette.light: Theme.raised
    palette.midlight: Theme.line
    palette.mid: Theme.lineStrong
    palette.dark: Theme.inkMuted
    palette.shadow: Theme.shadow
    palette.placeholderText: Theme.inkMuted
    palette.toolTipBase: Theme.dark ? "#2c332f" : "#2a3430"
    palette.toolTipText: "#f2f5f3"
    Binding { target: Theme; property: "mode"; value: root.pdf ? root.pdf.themeMode : "system" }
    property string uiFontFamily: Qt.platform.os === "windows" ? "Segoe UI Variable" : "Noto Sans CJK KR"
    font.family: uiFontFamily
    font.pixelSize: 14
    contentItem.enabled: !(root.tabWorkspace && root.tabWorkspace.closing)
    property var tabWorkspace: typeof documents !== "undefined" ? documents : null
    property var pdf: tabWorkspace ? tabWorkspace.activeBridge : bridge
    property bool switching: false
    property bool closeAllRequested: false
    function quitApplication() { closeAllRequested=true; close(); }
    property bool restoring: false
    property bool dialogsClear: !textDialog.visible && !annotationEditor.visible && !mergeDialog.visible && !ocrDialog.visible && !settingsDialog.visible && !errorDialog.visible && !aboutDialog.visible && !(tabWorkspace && tabWorkspace.closing)
    property bool tabActionsEnabled: dialogsClear && !presenting
    property bool externalOpenReady: dialogsClear && !readerMenuOpen && !tabMenu.visible && !switching
    property bool externalOpenPending: typeof externalRequests !== "undefined" && externalRequests.pending
    property bool presenting: false
    property var presentationState: null
    property bool readerMenuOpen: false
    property bool typingText: activeFocusItem instanceof TextInput || activeFocusItem instanceof TextEdit
    property bool pageKeysEnabled: hasDocument && !pageViewMode.activeFocus && !pageViewMode.popup.visible && !textDialog.visible && !mergeDialog.visible && !ocrDialog.visible && !settingsDialog.visible && !errorDialog.visible && !aboutDialog.visible && !typingText && !readerMenuOpen && !tabMenu.visible && !switching
    property var pendingNavigation: null
    property string tool: "read"
    readonly property var markupTools: ["highlight","underline","strikeout"]
    function isMarkupTool(value) { return markupTools.indexOf(value)>=0; }
    // Two modes only. The comment list is a side panel either mode can open;
    // page tools live in the sidebar all the time.
    property string workspaceMode: "read"
    property bool commentsOpen: false
    property real zoom: 1
    property bool twoPageView: false
    property int pageColumns: twoPageView ? 2 : 1
    function rowForPage(page) { return Math.floor(page/pageColumns); }
    function cellForPage(page) {
        var row=pages.itemAtIndex(rowForPage(page));
        return row ? row.pageItem(page%pageColumns) : null;
    }
    function cellTop(cell) { return cell.mapToItem(pages.contentItem,0,0).y; }
    function setTwoPageView(value) {
        if(twoPageView===value) return;
        var page=pdf.currentPage;
        restoring=true; twoPageView=value;
        Qt.callLater(function(){root.goPage(page);});
    }
    property bool sidebarOpen: true
    property string sidebarView: "pages"
    // zoom 1 means "fit width". The label shows the real size (100% = print size).
    function baseWidth() { return Math.max(80,(pages.width-64-16*(pageColumns-1))/pageColumns); }
    function actualZoom() {
        if(!hasDocument) return 1;
        return baseWidth()*zoom/(pdf.pageWidth(pdf.currentPage)*96/72);
    }
    property string zoomLabel: { pages.width; zoom; pdf.currentPage; pdf.document.count; return hasDocument ? Math.round(actualZoom()*100)+"%" : "—"; }
    function clampZoom(value) { return Math.max(.2, Math.min(4, value)); }
    function zoomBy(factor) { zoom=clampZoom(zoom*factor); }
    function setActualZoom(value) { if(hasDocument) zoom=clampZoom(value*pdf.pageWidth(pdf.currentPage)*96/72/baseWidth()); }
    function fitPage() {
        if(!hasDocument) return;
        var ratio=pdf.pageRatio(pdf.currentPage);
        zoom=clampZoom(Math.min(1,(pages.height-60)/ratio/baseWidth()));
        Qt.callLater(function(){ root.goPage(pdf.currentPage); });
    }
    property bool searchOpen: false
    property bool canAnnotate: pdf.document.annotatable === true && !pdf.busy && !pdf.ocrBusy && !textDialog.visible && !annotationEditor.visible
    onCommentsOpenChanged: if(pdf) pdf.setAnnotationPanelVisible(commentsOpen)
    onPdfChanged: { if(presenting) endPresentation(); if(pdf) pdf.setAnnotationPanelVisible(commentsOpen); }
    property bool canEdit: pdf.document.editable && !pdf.busy && !pdf.ocrBusy && !textDialog.visible && !annotationEditor.visible
    property bool hasDocument: pdf.document.count > 0
    property int draggedPage: -1
    property var draggedPages: []
    property int dropIndex: -1
    property real dragViewportY: 0
    property string pendingQuery: ""

    function goPage(page) {
        if (!Number.isFinite(page) || page < 0 || page >= pdf.document.count) return;
        navigationTimer.stop(); pendingNavigation=null;
        restoring=!presenting;
        pdf.selectPage(page, false, false);
        if(presenting) return;
        pages.cancelFlick();
        pages.positionViewAtIndex(rowForPage(page), ListView.Beginning);
        pendingNavigation={owner:pdf,page:page,offset:0,horizontal:pages.contentX/Math.max(1,pages.contentWidth),tries:0};
        navigationTimer.restart();
        if (tool === "editText") pdf.loadBlocks(page);
    }
    function turnPage(amount) {
        goPage(Math.max(0,Math.min(pdf.document.count-1,pdf.currentPage+amount*(presenting ? 1 : pageColumns))));
        if(presenting && presentation.item) presentation.item.forceActiveFocus();
        else pages.forceActiveFocus();
    }
    function startPresentation() {
        if(!hasDocument || !dialogsClear || readerMenuOpen || tabMenu.visible || pdf.busy || pdf.ocrBusy || presenting) return;
        var cell=cellForPage(pdf.currentPage);
        presentationState={owner:pdf,page:pdf.currentPage,offset:cell ? (pages.contentY-cellTop(cell))/cell.pageWidth : 0,
            horizontal:pages.contentX/Math.max(1,pages.contentWidth),visibility:visibility,x:x,y:y,width:width,height:height};
        navigationTimer.stop(); pendingNavigation=null; restoring=false;
        searchDelay.stop(); pages.cancelFlick();
        pdf.setPresentationActive(true); pdf.setAnnotationPanelVisible(false);
        presenting=true;
        showFullScreen();
        if(presentation.item) presentation.item.forceActiveFocus();
    }
    function endPresentation() {
        if(!presenting) return;
        var state=presentationState, owner=pdf, page=pdf.currentPage;
        presenting=false; restoring=true;
        if(state && state.owner) state.owner.setPresentationActive(false);
        if(state) {
            visibility=state.visibility;
            if(state.visibility===Window.Windowed) { x=state.x; y=state.y; width=state.width; height=state.height; }
        }
        pdf.setAnnotationPanelVisible(commentsOpen);
        Qt.callLater(function() {
            if(root.pdf!==owner || root.presenting || root.switching) return;
            pages.forceLayout();
            pages.positionViewAtIndex(rowForPage(page),ListView.Beginning);
            pendingNavigation={owner:owner,page:page,offset:state && state.owner===owner && state.page===page ? state.offset : 0,
                horizontal:state && state.owner===owner ? state.horizontal : 0,tries:0};
            if(root.hasDocument) navigationTimer.restart(); else root.restoring=false;
            pages.forceActiveFocus();
            if(root.tool==="editText" && root.hasDocument && !pdf.busy) pdf.loadBlocks(page);
            if(searchInput.text!==pdf.searchQuery) searchDelay.restart();
        });
    }
    function togglePresentation() { if(presenting) endPresentation(); else startPresentation(); }
    onHasDocumentChanged: if(!hasDocument && presenting) endPresentation()
    onVisibilityChanged: function(state) { if(presenting && state!==Window.FullScreen && state!==Window.Minimized) endPresentation(); }
    function saveView() {
        if (!tabWorkspace) return;
        if(presenting) endPresentation();
        searchDelay.stop(); navigationTimer.stop(); pendingNavigation=null;
        var page=pdf.currentPage, cell=cellForPage(page);
        tabWorkspace.rememberView({page:page,offset:cell ? (pages.contentY-cellTop(cell))/cell.pageWidth : 0,
            x:pages.contentX/Math.max(1,pages.contentWidth),zoom:zoom,twoPage:twoPageView,tool:tool,mode:workspaceMode,comments:commentsOpen,
            sidebar:sidebarOpen,sidebarView:sidebarView,search:searchOpen,query:searchInput.text});
        switching=true; restoring=true;
    }
    function restoreView() {
        var state=tabWorkspace.viewState, owner=pdf;
        twoPageView=!!state.twoPage; zoom=state.zoom || 1; tool=state.tool || "read"; workspaceMode=state.mode==="edit" ? "edit" : "read"; commentsOpen=!!state.comments;
        sidebarOpen=state.sidebar === undefined ? true : state.sidebar; searchOpen=!!state.search;
        sidebarView=state.sidebarView || "pages";
        searchInput.text=state.query === undefined ? pdf.searchQuery : state.query; pendingQuery=searchInput.text;
        switching=false;
        Qt.callLater(function() {
            if(root.pdf!==owner) return;
            var page=state.page === undefined ? pdf.currentPage : state.page;
            if (pdf.document.count>0) {
                pages.forceLayout(); pages.positionViewAtIndex(rowForPage(page),ListView.Beginning);
                pendingNavigation={owner:pdf,page:page,offset:state.offset || 0,horizontal:state.x || 0,tries:0};
                navigationTimer.restart();
            } else restoring=false;
            if (searchInput.text !== pdf.searchQuery) searchDelay.restart();
        });
    }
    function jumpTo(page,x,y) {
        if(page<0 || page>=pdf.document.count) return;
        if(presenting) { goPage(page); return; }
        restoring=true;
        root.goPage(page); pages.forceLayout();
        pendingNavigation={owner:pdf,page:page,x:x,y:y,tries:0};
        navigationTimer.restart();
    }
    // Bookmark targets: put the heading near the top, not a quarter down.
    function jumpToHeading(page,y) {
        if(page<0 || page>=pdf.document.count) return;
        root.goPage(page);
        if(presenting) return;
        var w=Math.max(1,pdf.pageWidth(page));
        pendingNavigation={owner:pdf,page:page,offset:y>60 ? Math.max(0,(y-24)/w) : 0,horizontal:pages.contentX/Math.max(1,pages.contentWidth),tries:0};
        navigationTimer.restart();
    }
    // Editing commits itself: clicking anywhere outside the box applies the
    // change (or just closes an untouched box). Clicking another paragraph
    // then opens it, located again after the page's text boxes refresh.
    property var pendingEditPoint: null
    property bool commitWhenReady: false
    function commitEdit(point) {
        if(!textDialog.visible || pdf.busy) return;
        pendingEditPoint=point || null;
        var live=pdf.liveEditor;
        if(textDialog.targetData.mode==="replace") {
            if(live.loading) { commitWhenReady=true; return; }
            if(!live.edited) { textDialog.close(); Qt.callLater(root.openPendingEdit); return; }
            if(live.canApply) { pdf.applyText(textDialog.targetData,textDialog.text,textDialog.fontSize,textDialog.areaHeight); return; }
            pendingEditPoint=null;   // keep the draft; the status bar says what to fix
        } else if(!textDialog.text.trim().length) { textDialog.close(); Qt.callLater(root.openPendingEdit); }
        else pdf.applyText(textDialog.targetData,textDialog.text,textDialog.fontSize,textDialog.areaHeight);
    }
    function openPendingEdit() {
        var point=pendingEditPoint;
        if(!point || textDialog.visible || pdf.busy || tool!=="editText") return;
        var blocks=pdf.blockBoxes(point.page);
        if(!blocks.length) { pdf.loadBlocksForPage(point.page); return; }   // retried on blocksChanged
        pendingEditPoint=null;
        for(var i=0;i<blocks.length;++i) {
            var r=blocks[i].displayRect;
            if(point.x>=r[0] && point.x<=r[2] && point.y>=r[1] && point.y<=r[3]) { pdf.editBlock(blocks[i]); return; }
        }
    }
    Connections {
        target: pdf.liveEditor
        function onChanged() { if(root.commitWhenReady && !pdf.liveEditor.loading) { root.commitWhenReady=false; root.commitEdit(root.pendingEditPoint); } }
    }
    // One line under the toolbar explaining what the current tool expects.
    function hintText() {
        if(tool==="editText") return textDialog.visible
            ? "다른 곳을 클릭하면 자동으로 적용돼요. 다른 문단을 누르면 바로 이어서 고칠 수 있어요 · Esc 취소 · Ctrl+S 파일 저장"
            : "고칠 문단을 클릭하세요. 다른 곳을 클릭하면 자동으로 적용돼요.";
        if(tool==="imageMove") return "이미지를 드래그해 이동하고, 오른쪽 아래 모서리로 크기를 조절하세요.";
        if(isMarkupTool(tool)) return "주석을 남길 글자를 드래그하세요.";
        if(tool==="note") return "페이지에서 메모를 남길 위치를 클릭하세요.";
        if(tool==="addText" || tool==="image") return "페이지 위에서 편집할 영역을 드래그하세요.";
        if(pdf.pageTextState==="restricted") return "문서 작성자가 텍스트 복사를 제한했어요.";
        if(pdf.ocrBusy) return "스캔의 글자를 인식하고 있어요. 문서는 계속 읽을 수 있습니다.";
        return "이 페이지에는 선택할 문자층이 없어요. OCR로 글자를 인식할 수 있습니다.";
    }
    // Closing the list also drops a comment tool, returning to the mode's own tool.
    function closeComments() {
        commentsOpen=false;
        if(tool==="note" || isMarkupTool(tool)) useTool(workspaceMode==="edit" ? "editText" : "read");
    }
    function useTool(value) {
        if(textDialog.visible || annotationEditor.visible) return;
        tool = value;
        if (value==="note") commentsOpen=true;
        else if (isMarkupTool(value)) {}
        else if (["read","hand"].indexOf(value)<0) workspaceMode = "edit";
        if (value === "editText") pdf.loadBlocks(pdf.currentPage);
    }
    onClosing: function(event) {
        if(annotationEditor.visible || textDialog.visible) {
            event.accepted=false; draftClose.open(); return;
        }
        if(externalOpenPending) {
            event.accepted=false; closeAllRequested=false; return;
        }
        if(tabWorkspace && !closeAllRequested && tabStrip.count>1) {
            event.accepted=false;
            tabWorkspace.closeTab(tabWorkspace.activeIndex);
            return;
        }
        event.accepted=tabWorkspace ? tabWorkspace.mayClose() : pdf.mayClose();
        closeAllRequested=false;
    }

    Shortcut { sequence: "Escape"; enabled: (textDialog.visible || annotationEditor.visible) && !pdf.busy && !errorDialog.visible && !fontChoice.popupOpen && !draftClose.visible; onActivated: { if(textDialog.visible) textDialog.close(); else annotationEditor.close(); } }
    Shortcut { sequence: "Ctrl+Shift+Q"; enabled: !pdf.busy && !draftClose.visible; onActivated: root.quitApplication() }
    Shortcut { sequence: "Ctrl+Tab"; enabled: !!root.tabWorkspace && root.tabActionsEnabled; onActivated: root.tabWorkspace.cycle(1) }
    Shortcut { sequence: "Ctrl+Shift+Tab"; enabled: !!root.tabWorkspace && root.tabActionsEnabled; onActivated: root.tabWorkspace.cycle(-1) }
    Shortcut { sequence: "Ctrl+W"; enabled: !!root.tabWorkspace && !pdf.busy && !draftClose.visible; onActivated: {if(textDialog.visible || annotationEditor.visible)root.close();else root.tabWorkspace.closeTab(root.tabWorkspace.activeIndex);} }
    Shortcut { sequence: "Ctrl+T"; enabled: !!root.tabWorkspace && root.tabActionsEnabled; onActivated: root.tabWorkspace.newTab() }
    Shortcut { sequence: "F3"; enabled: root.hasDocument && root.tabActionsEnabled; onActivated: pdf.findNext(searchInput.text,1) }
    Shortcut { sequence: "Shift+F3"; enabled: root.hasDocument && root.tabActionsEnabled; onActivated: pdf.findNext(searchInput.text,-1) }
    Shortcut { sequences: ["F5","F11","Ctrl+L"]; autoRepeat: false; enabled: root.hasDocument && root.dialogsClear; onActivated: root.togglePresentation() }
    Shortcut { sequences: ["Right","Down","PgDown","Space"]; enabled: root.pageKeysEnabled; onActivated: root.turnPage(1) }
    Shortcut { sequences: ["Left","Up","PgUp","Shift+Space"]; enabled: root.pageKeysEnabled; onActivated: root.turnPage(-1) }
    Shortcut { sequences: ["Home","Ctrl+Home"]; enabled: root.pageKeysEnabled; onActivated: root.goPage(0) }
    Shortcut { sequences: ["End","Ctrl+End"]; enabled: root.pageKeysEnabled; onActivated: root.goPage(pdf.document.count-1) }
    Shortcut { sequence: StandardKey.Open; enabled: root.tabActionsEnabled; onActivated: pdf.chooseOpen() }
    Shortcut { sequence: StandardKey.Print; enabled: root.tabActionsEnabled && root.hasDocument && !pdf.busy && !pdf.ocrBusy; onActivated: pdf.printDocument() }
    Shortcut { sequence: StandardKey.SelectAll; enabled: root.tabActionsEnabled && root.tool === "read" && !root.typingText; onActivated: pdf.selectAllText() }
    Shortcut { sequence: StandardKey.Save; enabled: root.tabActionsEnabled; onActivated: pdf.save(false) }
    Shortcut { sequence: StandardKey.SaveAs; enabled: root.tabActionsEnabled; onActivated: pdf.save(true) }
    Shortcut { sequences: [StandardKey.Undo]; enabled: root.tabActionsEnabled && (root.canEdit || root.canAnnotate) && pdf.document.canUndo; onActivated: pdf.undo() }
    Shortcut { sequences: [StandardKey.Redo]; enabled: root.tabActionsEnabled && (root.canEdit || root.canAnnotate) && pdf.document.canRedo; onActivated: pdf.redo() }
    Shortcut { sequence: StandardKey.Find; enabled: root.tabActionsEnabled; onActivated: { root.searchOpen = true; root.sidebarOpen = true; searchInput.forceActiveFocus(); } }
    Shortcut { sequences: [StandardKey.Copy]; enabled: root.tabActionsEnabled && !root.typingText; onActivated: pdf.copySelection() }
    Shortcut { sequences: ["Ctrl++","Ctrl+="]; enabled: root.tabActionsEnabled; onActivated: root.zoomBy(1.15) }
    Shortcut { sequence: "Ctrl+-"; enabled: root.tabActionsEnabled; onActivated: root.zoomBy(1/1.15) }
    Shortcut { sequence: "Ctrl+0"; enabled: root.tabActionsEnabled; onActivated: root.zoom = 1 }
    Shortcut { sequence: "Escape"; enabled: root.dialogsClear && !root.readerMenuOpen && !tabMenu.visible; onActivated: { if(root.presenting) root.endPresentation(); else root.useTool("read"); } }
    Shortcut { sequence: "Ctrl+Shift+R"; enabled: root.canEdit && root.tabActionsEnabled; onActivated: pdf.rotateSelected() }
    Shortcut { sequence: "Alt+Up"; enabled: root.canEdit && root.tabActionsEnabled; onActivated: pdf.moveSelected(-1) }
    Shortcut { sequence: "Alt+Down"; enabled: root.canEdit && root.tabActionsEnabled; onActivated: pdf.moveSelected(1) }

    header: ColumnLayout {
        objectName: "readerHeader"; visible: !root.presenting
        enabled: !(root.tabWorkspace && root.tabWorkspace.closing)
        spacing: 0
        // Row 1 · brand and document tabs. Tabs can be dragged to reorder.
        Rectangle {
            Layout.fillWidth: true; implicitHeight: 42; color: Theme.chrome
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 14; anchors.rightMargin: 10; spacing: 6
                Image { source: "../assets/icon.svg"; sourceSize: Qt.size(48,48); Layout.preferredWidth: 22; Layout.preferredHeight: 22 }
                Text { text: "윤DF"; font.pixelSize: 14; font.weight: Font.DemiBold; color: Theme.ink; Layout.rightMargin: 8 }
                Text {
                    visible: !root.tabWorkspace; Layout.fillWidth: true; elide: Text.ElideMiddle
                    text: root.hasDocument ? pdf.document.name : ""; font.pixelSize: 13; color: Theme.inkSoft
                }
                ListView {
                    id: tabStrip; objectName: "documentTabs"; visible: !!root.tabWorkspace
                    Layout.fillWidth: true; Layout.fillHeight: true
                    orientation: ListView.Horizontal; spacing: 2; clip: true; interactive: false
                    boundsBehavior: Flickable.StopAtBounds
                    model: root.tabWorkspace ? root.tabWorkspace.tabModel : null
                    property int draggingIndex: -1
                    function syncIndex() {
                        currentIndex=root.tabWorkspace ? root.tabWorkspace.activeIndex : 0;
                        positionViewAtIndex(currentIndex,ListView.Contain);
                    }
                    Connections { target: root.tabWorkspace; function onIndexChanged() { tabStrip.syncIndex(); } }
                    Component.onCompleted: syncIndex()
                    onCurrentIndexChanged: positionViewAtIndex(currentIndex,ListView.Contain)
                    onCountChanged: Qt.callLater(syncIndex)
                    WheelHandler { onWheel: function(event) { tabStrip.contentX=Math.max(0,Math.min(tabStrip.contentWidth-tabStrip.width,tabStrip.contentX-(event.angleDelta.y+event.angleDelta.x)/2)); } }
                    delegate: Item {
                        id: documentTab; required property var modelData; required property int index
                        objectName: "documentTab"+index
                        readonly property bool current: index===root.tabWorkspace.activeIndex
                        property real dragOffset: 0
                        width: Math.min(230,Math.max(150,tabTitle.implicitWidth+62)); height: tabStrip.height
                        z: tabDrag.active ? 10 : current ? 2 : 1
                        transform: Translate { x: documentTab.dragOffset }
                        Rectangle {
                            anchors.fill: parent; anchors.topMargin: 6
                            radius: Theme.radius
                            color: documentTab.current ? Theme.surface : tabMouse.containsMouse || tabDrag.active ? Theme.hover : "transparent"
                            border.color: documentTab.current && Theme.dark ? Theme.line : "transparent"
                            // Square off the bottom so the active tab joins the toolbar.
                            Rectangle { visible: documentTab.current; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: Theme.radius; color: Theme.surface }
                            opacity: tabDrag.active ? .92 : 1
                        }
                        Rectangle { visible: !documentTab.current && documentTab.index+1!==root.tabWorkspace.activeIndex && !tabMouse.containsMouse; anchors.right: parent.right; y: 16; width: 1; height: 16; color: Theme.lineStrong }
                        MouseArea {
                            id: tabMouse; anchors.fill: parent; anchors.topMargin: 6; hoverEnabled: true; acceptedButtons: Qt.LeftButton | Qt.MiddleButton
                            enabled: root.tabActionsEnabled
                            onClicked: function(event){ if(event.button===Qt.MiddleButton) root.tabWorkspace.closeId(documentTab.modelData.id); else root.tabWorkspace.activateId(documentTab.modelData.id); }
                        }
                        DragHandler {
                            id: tabDrag; target: null; yAxis.enabled: false; enabled: root.tabActionsEnabled && tabStrip.count>1
                            onActiveChanged: {
                                if(active) { tabStrip.draggingIndex=documentTab.index; root.tabWorkspace.activateId(documentTab.modelData.id); return; }
                                var step=documentTab.width+tabStrip.spacing;
                                var target=Math.max(0,Math.min(tabStrip.count-1,documentTab.index+Math.round(documentTab.dragOffset/step)));
                                var from=documentTab.index;
                                documentTab.dragOffset=0; tabStrip.draggingIndex=-1;
                                if(target!==from) root.tabWorkspace.moveTab(from,target);
                            }
                            onTranslationChanged: if(active) documentTab.dragOffset=translation.x
                        }
                        ToolTip.visible: tabMouse.containsMouse && !tabDrag.active; ToolTip.delay: 700; ToolTip.text: (modelData.path || "새 문서")+"\n끌어서 순서를 바꿀 수 있어요."
                        RowLayout {
                            anchors.fill: parent; anchors.topMargin: 6; anchors.leftMargin: 12; anchors.rightMargin: 4; spacing: 7
                            Rectangle { width: 6; height: 6; radius: 3; color: documentTab.modelData.dirty ? Theme.dirty : documentTab.modelData.busy ? Theme.accent : "transparent" }
                            Text { id: tabTitle; text: documentTab.modelData.name; Layout.fillWidth: true; elide: Text.ElideMiddle; color: documentTab.current ? Theme.ink : Theme.inkSoft; font.pixelSize: 12; font.weight: documentTab.current ? Font.DemiBold : Font.Normal }
                            ActionButton { objectName: "closeTab"+documentTab.index; glyph: "close"; compact: true; implicitWidth: 24; implicitHeight: 24; hint: "탭 닫기 · Ctrl+W"; enabled: root.tabActionsEnabled; opacity: documentTab.current || tabMouse.containsMouse || hovered ? 1 : 0; onClicked: root.tabWorkspace.closeId(documentTab.modelData.id) }
                        }
                    }
                }
                ActionButton { visible: !!root.tabWorkspace; glyph: "add"; compact: true; hint: "새 탭 · Ctrl+T"; enabled: root.tabActionsEnabled; onClicked: root.tabWorkspace.newTab() }
                ActionButton { visible: !!root.tabWorkspace; objectName: "openDocumentsButton"; glyph: "down"; compact: true; hint: "열린 문서 목록"; enabled: root.tabActionsEnabled; onClicked: tabMenu.popup() }
            }
            Menu {
                id: tabMenu; objectName: "openDocumentsMenu"
                Repeater {
                    model: root.tabWorkspace ? root.tabWorkspace.tabModel : null
                    MenuItem { required property var modelData; required property int index; text: (modelData.dirty ? "● " : "")+modelData.name; checkable: true; checked: index===root.tabWorkspace.activeIndex; onTriggered: root.tabWorkspace.activateId(modelData.id) }
                }
            }
        }
        // Row 2 · one toolbar: modes on the left, view and file actions on the right.
        Rectangle {
            Layout.fillWidth: true; implicitHeight: 50; color: Theme.surface
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12; spacing: 4
                ActionButton { glyph: "sidebar"; hint: "사이드바 · 페이지와 목차"; active: root.sidebarOpen; onClicked: root.sidebarOpen=!root.sidebarOpen }
                ToolSeparator {}
                Rectangle {
                    implicitWidth: modeRow.implicitWidth+6; implicitHeight: 36; radius: Theme.radius+2; color: Theme.surfaceAlt; border.color: Theme.line
                    Row {
                        id: modeRow; anchors.centerIn: parent; spacing: 2
                        ActionButton { objectName: "readModeButton"; compact: true; enabled: !textDialog.visible && !annotationEditor.visible; text: "읽기"; active: root.workspaceMode === "read"; onClicked: { root.workspaceMode="read"; root.useTool("read"); } }
                        ActionButton { objectName: "editModeButton"; compact: true; text: "편집"; active: root.workspaceMode === "edit"; enabled: root.hasDocument && !textDialog.visible && !annotationEditor.visible; onClicked: { root.workspaceMode="edit"; root.useTool("editText"); } }
                    }
                }
                ActionButton { visible: root.workspaceMode !== "edit"; glyph: "text"; hint: "텍스트 선택"; active: root.tool === "read"; enabled: root.hasDocument; Layout.leftMargin: 6; onClicked: root.useTool("read") }
                ActionButton { visible: root.workspaceMode !== "edit"; glyph: "hand"; hint: "손 도구 · 끌어서 이동"; active: root.tool === "hand"; enabled: root.hasDocument; onClicked: root.useTool("hand") }
                Item { Layout.fillWidth: true }
                ComboBox {
                    id: pageViewMode; objectName: "pageViewMode"; implicitWidth: 104; implicitHeight: 32; model: ["한 페이지", "두 페이지"]
                    enabled: root.hasDocument && !textDialog.visible; currentIndex: root.twoPageView ? 1 : 0
                    font.pixelSize: 13
                    contentItem: Text { leftPadding: 10; text: pageViewMode.displayText; font: pageViewMode.font; color: Theme.inkSoft; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                    background: Rectangle { radius: Theme.radius; color: pageViewMode.hovered ? Theme.hover : "transparent"; border.color: Theme.line }
                    indicator: Icon { name: "down"; size: 14; x: parent.width-width-9; y: (parent.height-height)/2 }
                    opacity: enabled ? 1 : .38
                    onActivated: root.setTwoPageView(currentIndex===1)
                }
                ActionButton { glyph: "minus"; hint: "축소 · Ctrl+-"; enabled: root.hasDocument; Layout.leftMargin: 6; onClicked: root.zoomBy(1/1.15) }
                ActionButton {
                    id: zoomButton; objectName: "zoomButton"; implicitWidth: 64; enabled: root.hasDocument
                    text: root.zoomLabel; hint: "배율 선택 · Ctrl+0 너비 맞춤"
                    onClicked: zoomMenu.popup(zoomButton, 0, zoomButton.height+4)
                    Menu {
                        id: zoomMenu
                        MenuItem { text: "너비 맞춤"; onTriggered: root.zoom=1 }
                        MenuItem { text: "페이지 맞춤"; onTriggered: root.fitPage() }
                        MenuSeparator {}
                        Repeater {
                            model: [50,75,100,125,150,200,300]
                            MenuItem { required property int modelData; text: modelData+"%"; onTriggered: root.setActualZoom(modelData/100) }
                        }
                    }
                }
                ActionButton { glyph: "add"; hint: "확대 · Ctrl++"; enabled: root.hasDocument; onClicked: root.zoomBy(1.15) }
                ToolSeparator {}
                ActionButton { objectName: "commentsModeButton"; glyph: "note"; hint: "주석 목록"; active: root.commentsOpen; enabled: root.hasDocument && !annotationEditor.visible; onClicked: root.commentsOpen=!root.commentsOpen }
                ActionButton { glyph: "search"; hint: "문서 검색 · Ctrl+F"; active: root.searchOpen; enabled: root.hasDocument; onClicked: { root.searchOpen=!root.searchOpen; root.sidebarOpen=true; if(root.searchOpen) searchInput.forceActiveFocus(); } }
                ActionButton { objectName: "presentationButton"; glyph: "present"; hint: "슬라이드 쇼 · F5"; enabled: root.hasDocument && !pdf.busy && !pdf.ocrBusy; onClicked: root.startPresentation() }
                ActionButton { objectName: "printButton"; glyph: "print"; hint: "인쇄 · Ctrl+P"; enabled: root.tabActionsEnabled && root.hasDocument && pdf.document.printable && !pdf.busy && !pdf.ocrBusy; onClicked: pdf.printDocument() }
                ToolSeparator {}
                ActionButton { glyph: "open"; hint: "열기 · Ctrl+O"; enabled: root.tabActionsEnabled && !pdf.busy && !pdf.ocrBusy; onClicked: pdf.chooseOpen() }
                ActionButton { objectName: "saveButton"; text: "저장"; primary: root.hasDocument && pdf.document.dirty; outlined: !(root.hasDocument && pdf.document.dirty); implicitWidth: 64; hint: "저장 · Ctrl+S"; enabled: root.tabActionsEnabled && root.hasDocument && !pdf.busy && !pdf.ocrBusy; onClicked: pdf.save(false) }
                ActionButton { objectName: "settingsButton"; glyph: "settings"; hint: "설정"; onClicked: settingsDialog.open() }
                ActionButton {
                    id: moreButton; objectName: "moreButton"; glyph: "more"; hint: "더 보기"
                    onClicked: moreMenu.popup(moreButton, moreButton.width-moreMenu.width, moreButton.height+4)
                    Menu {
                        id: moreMenu; width: 240
                        MenuItem { objectName: "mergeButton"; text: "PDF 결합…"; enabled: root.tabActionsEnabled && !pdf.busy && !pdf.ocrBusy; onTriggered: pdf.showMerge() }
                        MenuItem { text: "다른 이름으로 저장…"; enabled: root.tabActionsEnabled && root.hasDocument && !pdf.busy && !pdf.ocrBusy; onTriggered: pdf.save(true) }
                        MenuItem { text: "문자 인식 (OCR)…"; enabled: root.canEdit; onTriggered: { pdf.inspectOcr(); ocrDialog.open(); } }
                        MenuSeparator {}
                        MenuItem { text: Theme.dark ? "밝은 화면으로" : "어두운 화면으로"; onTriggered: pdf.setThemeMode(Theme.dark ? "light" : "dark") }
                        MenuItem { text: "윤DF 정보"; onTriggered: aboutDialog.open() }
                    }
                }
            }
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.line }
        }
        Rectangle {
            visible: textDialog.visible; Layout.fillWidth: true; height: visible ? 50 : 0; color: Theme.accentSoft
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.line }
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 14; anchors.rightMargin: 12; spacing: 8
                Icon { name: "edit"; tone: Theme.accentInk }
                Text { text: "본문 편집 중"; color: Theme.accentInk; font.weight: Font.DemiBold; Layout.rightMargin: 6 }
                FontPicker { id: fontChoice; controller: root.pdf; Layout.fillWidth: true; Layout.maximumWidth: 320; enabled: !pdf.busy }
                ActionButton { text: "글꼴 파일"; enabled: !pdf.busy; onClicked: pdf.chooseFont() }
                TextField { id: sizeInput; objectName: "fontSizeInput"; Layout.preferredWidth: 62; text: textDialog.fontSize.toFixed(2); validator: DoubleValidator { bottom:4; top:200 } selectByMouse: true; onTextEdited: if(acceptableInput) {textDialog.fontSize=Number(text);pdf.liveEditor.setSize(Number(text));} }
                Text { text: "pt"; color: Theme.inkMuted }
                Text { text: textDialog.targetData.mode==="replace" ? "자동 줄바꿈" : "높이"; color: Theme.inkMuted }
                TextField { visible: textDialog.targetData.mode!=="replace"; objectName: "inlineHeightInput"; Layout.preferredWidth: 62; text: textDialog.areaHeight.toFixed(0); validator: DoubleValidator { bottom:5; top:20000 } selectByMouse: true; onTextEdited: if(acceptableInput) textDialog.areaHeight=Number(text) }
                Item { Layout.fillWidth: true }
                ActionButton { objectName: "cancelTextButton"; text: "취소"; enabled: !pdf.busy; onClicked: {root.closeAfterEdit=false;textDialog.close();} }
                ActionButton { objectName: "applyTextButton"; text: "적용"; primary: true; enabled: !pdf.busy && (textDialog.targetData.mode!=="replace" || pdf.liveEditor.canApply); onClicked: pdf.applyText(textDialog.targetData,textDialog.text,textDialog.fontSize,textDialog.areaHeight) }
            }
        }
        Rectangle {
            visible: textDialog.visible && textDialog.targetData.mode==="replace" && pdf.liveEditor.status.length>0
            Layout.fillWidth: true; height: visible ? statusLabel.implicitHeight+16 : 0; color: Theme.warnSurface
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 16; anchors.rightMargin: 10
                Text { id: statusLabel; objectName: "inlineFontStatus"; Layout.fillWidth: true; text: pdf.liveEditor.status; wrapMode: Text.WordWrap; color: Theme.warnInk; font.pixelSize: 13 }
                ActionButton { objectName: "useMissingFont"; visible: pdf.liveEditor.canUseFallback; text: "없는 글자만 대체"; implicitHeight: 28; onClicked: pdf.liveEditor.useFallback() }
                ActionButton { objectName: "retryFont"; visible: !pdf.liveEditor.loading && !pdf.liveEditor.canApply; text: "다시 시도"; implicitHeight: 28; onClicked: pdf.liveEditor.retry() }
            }
        }
        Rectangle {
            visible: root.hasDocument && ((root.tool !== "read" && root.tool !== "hand") || pdf.pageTextState === "empty" || pdf.pageTextState === "restricted")
            Layout.fillWidth: true; height: visible ? 34 : 0; color: Theme.surfaceAlt
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.line }
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 16; anchors.rightMargin: 12; spacing: 8
                Icon { name: "check"; size: 14; tone: Theme.inkMuted; visible: root.tool !== "read" && root.tool !== "hand" }
                Text {
                    Layout.fillWidth: true; font.pixelSize: 12; color: Theme.inkSoft; elide: Text.ElideRight
                    text: root.hintText()
                }
                ActionButton { visible: pdf.pageTextState === "empty" && !pdf.ocrBusy; implicitHeight: 27; text: "이 페이지 OCR"; enabled: root.canEdit; onClicked: pdf.recognizeCurrentPage() }
            }
        }
    }

    RowLayout {
        objectName: "readerWorkspace"; visible: !root.presenting
        anchors.fill: parent; spacing: 0
        Rectangle {
            visible: root.sidebarOpen
            Layout.preferredWidth: 224; Layout.fillHeight: true; color: Theme.surfaceAlt
            ColumnLayout {
                anchors.fill: parent; spacing: 0
                RowLayout {
                    Layout.fillWidth: true; Layout.leftMargin: 10; Layout.rightMargin: 12; Layout.topMargin: 10; Layout.bottomMargin: 6; spacing: 2
                    visible: !root.searchOpen
                    ActionButton { objectName: "sidebarPagesTab"; compact: true; text: "페이지"; active: root.sidebarView==="pages"; onClicked: root.sidebarView="pages" }
                    ActionButton { objectName: "sidebarOutlineTab"; compact: true; text: "목차"; active: root.sidebarView==="outline"; enabled: root.hasDocument; onClicked: root.sidebarView="outline" }
                    Item { Layout.fillWidth: true }
                    Text { text: pdf.selection.length > 1 ? pdf.selection.length + "개 선택" : root.hasDocument ? (pdf.currentPage+1) + " / " + pdf.document.count : ""; color: Theme.inkMuted; font.pixelSize: 12 }
                }
                RowLayout {
                    visible: root.searchOpen
                    Layout.fillWidth: true; Layout.margins: 13; spacing: 5
                    Text { text: "문서 검색"; font.weight: Font.DemiBold; font.pixelSize: 14; color: Theme.ink; Layout.fillWidth: true }
                    ActionButton { glyph: "close"; compact: true; hint: "검색 닫기"; onClicked: root.searchOpen=false }
                }
                ColumnLayout {
                    visible: root.searchOpen; Layout.fillWidth: true; Layout.leftMargin: 12; Layout.rightMargin: 12; spacing: 9
                    TextField {
                        id: searchInput; objectName: "searchInput"; Layout.fillWidth: true
                        placeholderText: "문서에서 찾기"; selectByMouse: true; font.pixelSize: 14
                        leftPadding: 10; rightPadding: 10; color: Theme.ink; selectionColor: Theme.selection; selectedTextColor: Theme.ink
                        placeholderTextColor: Theme.inkMuted
                        background: Rectangle { radius: Theme.radiusSmall; color: Theme.field; border.width: searchInput.activeFocus ? 2 : 1; border.color: searchInput.activeFocus ? Theme.focusRing : Theme.lineStrong }
                        onTextEdited: { root.pendingQuery = text; searchDelay.restart(); }
                        onAccepted: { searchDelay.stop(); pdf.findNext(text,1); }
                        Keys.onPressed: function(event) {
                            if((event.key===Qt.Key_Return || event.key===Qt.Key_Enter) && (event.modifiers & Qt.ShiftModifier)) {
                                searchDelay.stop(); pdf.findNext(text,-1); event.accepted=true;
                            }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true; spacing: 2
                        Text { Layout.fillWidth: true; text: pdf.searchCount ? (pdf.searchIndex+1)+" / "+pdf.searchCount+(pdf.searching ? " · 검색 중" : "곳") : pdf.searching ? "검색 중…" : pdf.searchQuery ? "검색 결과 없음" : "검색어를 입력하세요"; color: Theme.inkMuted; font.pixelSize: 12 }
                        ActionButton { objectName: "previousSearchHit"; glyph: "up"; compact: true; hint: "이전 결과 · Shift+Enter"; enabled: pdf.searchCount>0; onClicked: pdf.findNext(searchInput.text,-1) }
                        ActionButton { objectName: "nextSearchHit"; glyph: "down"; compact: true; hint: "다음 결과 · Enter / F3"; enabled: pdf.searchCount>0; onClicked: pdf.findNext(searchInput.text,1) }
                    }
                    ListView {
                        Layout.fillWidth: true; Layout.preferredHeight: Math.min(180, contentHeight); clip: true
                        model: pdf.searchResults
                        delegate: ItemDelegate {
                            required property var modelData
                            width: ListView.view.width; height: 34
                            objectName: "searchResult"+modelData.page
                            highlighted: pdf.activeSearchHit.page === modelData.page
                            contentItem: Text { text: (modelData.page+1) + "페이지  ·  " + modelData.count + "곳"; color: Theme.ink; font.pixelSize: 13; verticalAlignment: Text.AlignVCenter }
                            background: Rectangle { radius: Theme.radiusSmall; color: parent.highlighted ? Theme.accentSoft : parent.hovered ? Theme.hover : "transparent" }
                            onClicked: pdf.selectSearchHit(modelData.firstHit)
                        }
                    }
                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.line; Layout.bottomMargin: 8 }
                }
                ListView {
                    id: outlineList; objectName: "outlineList"
                    visible: root.sidebarView==="outline" && !root.searchOpen
                    Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                    leftMargin: 8; rightMargin: 8; bottomMargin: 12
                    model: root.switching ? [] : pdf.outline
                    ScrollBar.vertical: ScrollBar { }
                    // The entry for the page being read, so the reader sees where they are.
                    property int currentEntry: {
                        var best=-1, items=pdf.outline;
                        for(var i=0;i<items.length;++i) if(items[i].page>=0 && items[i].page<=pdf.currentPage) best=i;
                        return best;
                    }
                    delegate: ItemDelegate {
                        id: outlineItem; required property var modelData; required property int index
                        objectName: "outlineItem"+index
                        width: outlineList.width-16; height: Math.max(32, outlineText.implicitHeight+14)
                        enabled: modelData.page>=0
                        leftPadding: 10+Math.min(modelData.level-1,4)*14; rightPadding: 8
                        contentItem: RowLayout {
                            spacing: 6
                            Text {
                                id: outlineText; Layout.fillWidth: true; text: outlineItem.modelData.title; wrapMode: Text.Wrap; maximumLineCount: 3; elide: Text.ElideRight
                                font.pixelSize: 13; font.weight: outlineItem.modelData.level===1 ? Font.Medium : Font.Normal
                                color: outlineItem.index===outlineList.currentEntry ? Theme.accentInk : outlineItem.modelData.level===1 ? Theme.ink : Theme.inkSoft
                            }
                            Text { text: outlineItem.modelData.page>=0 ? outlineItem.modelData.page+1 : ""; font.pixelSize: 11; color: Theme.inkMuted; Layout.alignment: Qt.AlignTop; topPadding: 2 }
                        }
                        background: Rectangle { radius: Theme.radiusSmall; color: outlineItem.index===outlineList.currentEntry ? Theme.accentSoft : outlineItem.hovered ? Theme.hover : "transparent" }
                        onClicked: pdf.openOutline(index)
                    }
                    Column {
                        visible: outlineList.count===0; anchors.centerIn: parent; width: parent.width-40; spacing: 6
                        Text { width: parent.width; horizontalAlignment: Text.AlignHCenter; text: "목차가 없어요"; color: Theme.inkSoft; font.pixelSize: 13; font.weight: Font.Medium }
                        Text { width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; text: "이 PDF에는 책갈피가 들어 있지 않아요. 페이지 탭에서 미리보기로 이동할 수 있어요."; color: Theme.inkMuted; font.pixelSize: 12; lineHeight: 1.3 }
                    }
                }
                ListView {
                    id: thumbs; objectName: "thumbnailList"
                    visible: root.sidebarView==="pages" || root.searchOpen
                    Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                    model: root.switching ? 0 : pdf.document.count; spacing: 12; topMargin: 4; bottomMargin: 16
                    ScrollBar.vertical: ScrollBar { }
                    delegate: Item {
                        id: thumbCell
                        required property int index
                        width: thumbs.width; height: 188
                        property bool selected: pdf.selection.indexOf(index) >= 0
                        property bool near: !root.presenting && y+height >= thumbs.contentY-150 && y <= thumbs.contentY+thumbs.height+150
                        property string pageImage: ""
                        property string renderError: ""
                        property real pageRatio: pdf.pageRatio(index)
                        function request() {
                            pageImage=pdf.imageUrl(index,"thumb");renderError=pdf.imageError(index,"thumb");pageRatio=pdf.pageRatio(index);
                            if (near) pdf.requestPage(index,"thumb",Math.ceil(144*Screen.devicePixelRatio));
                            else pdf.releasePage(index,"thumb");
                        }
                        onNearChanged: request()
                        Component.onCompleted: request()
                        Connections {
                            target: root.pdf
                            function onStateChanged() { thumbCell.request(); }
                            function onPageImageChanged(page,kind) { if(page===thumbCell.index && kind==="thumb") { thumbCell.pageImage=pdf.imageUrl(page,kind);thumbCell.renderError=pdf.imageError(page,kind); } }
                            function onPageMetricsChanged(page) { if(page===thumbCell.index) thumbCell.pageRatio=pdf.pageRatio(page); }
                        }
                        Timer { interval: 700; repeat: true; running: thumbCell.near && !thumbCell.pageImage && !thumbCell.renderError; onTriggered: thumbCell.request() }
                        Rectangle {
                            id: thumbVisual
                            anchors.horizontalCenter: parent.horizontalCenter; y: 2; width: 164; height: 163; radius: 9
                            color: thumbCell.selected ? Theme.accentSoft : thumbHover.hovered ? Theme.hover : "transparent"
                            border.color: thumbCell.selected ? Theme.accent : "transparent"; border.width: thumbCell.selected ? 1.5 : 1
                            HoverHandler { id: thumbHover }
                            Rectangle {
                                objectName: "thumbnailPaper"+thumbCell.index
                                anchors.centerIn: parent; width: Math.min(138,145/thumbCell.pageRatio); height: width*thumbCell.pageRatio
                                color: "white"; border.color: pdf.currentPage===thumbCell.index ? Theme.accent : Theme.pageEdge
                                border.width: pdf.currentPage===thumbCell.index ? 2 : 1
                                Image { objectName: "thumbnailImage"+thumbCell.index; anchors.fill: parent; anchors.margins: 1; source: thumbCell.pageImage; fillMode: Image.Stretch; cache: false; asynchronous: true; retainWhileLoading: true; smooth: true }
                                BusyIndicator { anchors.centerIn: parent; width: 20; height: 20; running: !thumbCell.pageImage && !thumbCell.renderError; visible: running }
                                ActionButton { anchors.centerIn: parent; visible: !thumbCell.pageImage && !!thumbCell.renderError; text: "재시도"; hint: thumbCell.renderError; onClicked: pdf.retryPage(thumbCell.index,"thumb",Math.ceil(144*Screen.devicePixelRatio)) }
                            }
                            Rectangle { visible: pdf.currentPage===thumbCell.index; x: 6; y: parent.height/2-12; width: 3; height: 24; radius: 2; color: Theme.accent
                            }
                            Drag.active: dragHandler.active
                            Drag.source: thumbCell
                            Drag.hotSpot.x: 70; Drag.hotSpot.y: 80
                            opacity: dragHandler.active ? .6 : 1
                            Text { visible: dragHandler.active; anchors.top: parent.top; anchors.right: parent.right; text: root.draggedPages.length+"장 이동"; color: Theme.accentInk; font.bold: true; z: 10 }
                            DragHandler {
                                id: dragHandler; target: null; enabled: root.canEdit
                                onActiveChanged: {
                                    if (active) { if(pdf.selection.indexOf(thumbCell.index)<0) pdf.selectPage(thumbCell.index,false,false); root.draggedPages=pdf.selection.slice(); root.draggedPage = thumbCell.index; root.dropIndex = -1; }
                                    else {
                                        if (root.draggedPage >= 0 && root.dropIndex >= 0) pdf.moveSelectionTo(root.dropIndex);
                                        root.draggedPage = -1; root.dropIndex = -1; root.draggedPages=[];
                                    }
                                }
                                onCentroidChanged: {
                                    if (!active) return;
                                    var p = thumbVisual.mapToItem(thumbs.contentItem, centroid.position.x, centroid.position.y);
                                    root.dragViewportY = thumbVisual.mapToItem(thumbs, centroid.position.x, centroid.position.y).y;
                                    var targetIndex = thumbs.indexAt(thumbs.width/2, p.y);
                                    if (targetIndex >= 0) { var cell=thumbs.itemAtIndex(targetIndex); root.dropIndex=targetIndex+(cell && p.y>cell.y+cell.height/2 ? 1 : 0); } else if(p.y>=thumbs.contentHeight+thumbs.originY) root.dropIndex=pdf.document.count;
                                }
                            }
                            TapHandler {
                                acceptedButtons: Qt.LeftButton
                                onTapped: function(eventPoint) {
                                    pdf.selectPointer(thumbCell.index);
                                    pages.positionViewAtIndex(root.rowForPage(thumbCell.index), ListView.Beginning);
                                    pages.forceActiveFocus();
                                    if (root.tool === "editText") pdf.loadBlocks(thumbCell.index);
                                }
                            }
                        }
                        Rectangle { visible: root.dropIndex === thumbCell.index || (thumbCell.index===pdf.document.count-1 && root.dropIndex===pdf.document.count); x: 26; y: root.dropIndex===pdf.document.count ? parent.height-2 : 0; width: parent.width-52; height: 3; color: Theme.accent; radius: 2 }
                        Text { anchors.horizontalCenter: parent.horizontalCenter; y: 172; text: thumbCell.index+1; font.pixelSize: 12; color: thumbCell.selected || pdf.currentPage===thumbCell.index ? Theme.accentInk : Theme.inkMuted; font.weight: thumbCell.selected ? Font.DemiBold : Font.Normal }
                    }
                }
                Rectangle { visible: root.sidebarView==="pages"; Layout.fillWidth: true; height: 1; color: Theme.line }
                ColumnLayout {
                    visible: root.sidebarView==="pages"
                    Layout.fillWidth: true; Layout.margins: 9; spacing: 2
                    RowLayout {
                        spacing: 2; Layout.alignment: Qt.AlignHCenter
                        ActionButton { glyph: "up"; text: ""; hint: "위로 · Alt+↑"; enabled: root.canEdit; onClicked: pdf.moveSelected(-1) }
                        ActionButton { glyph: "down"; text: ""; hint: "아래로 · Alt+↓"; enabled: root.canEdit; onClicked: pdf.moveSelected(1) }
                        ActionButton { glyph: "rotate"; text: ""; hint: "회전"; enabled: root.canEdit; onClicked: pdf.rotateSelected() }
                    }
                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter; spacing: 4
                        ActionButton { glyph: "add"; text: "PDF 삽입"; enabled: root.canEdit; onClicked: pdf.insertPdf() }
                        ActionButton { glyph: "delete"; text: "삭제"; enabled: root.canEdit; onClicked: pdf.deleteSelected() }
                    }
                }
            }
            Rectangle { anchors.right: parent.right; height: parent.height; width: 1; color: Theme.line }
        }

        Rectangle {
            id: workspace; Layout.fillWidth: true; Layout.fillHeight: true; color: Theme.canvas
            TapHandler { onPressedChanged: if(pressed) { if(textDialog.visible) root.commitEdit(null); pages.forceActiveFocus(); } }
            ListView {
                id: pages; objectName: "pageList"; anchors.fill: parent; clip: true
                visible: root.hasDocument
                model: root.switching ? 0 : Math.ceil(pdf.document.count/root.pageColumns); spacing: 18; topMargin: 24; bottomMargin: 24
                cacheBuffer: Math.max(1200,height*2)
                contentWidth: Math.max(width, (width-64)*root.zoom+64)
                flickableDirection: Flickable.AutoFlickDirection
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn }
                ScrollBar.horizontal: ScrollBar { }
                onContentYChanged: {
                    var idx = indexAt(contentWidth/2, contentY+height*.33);
                    if (idx >= 0 && !root.switching && !root.restoring && !root.presenting) { var first=idx*root.pageColumns; if(pdf.currentPage<first || pdf.currentPage>=first+root.pageColumns) pdf.setCurrentPage(first); }
                }
                delegate: Item {
                    id: spreadRow
                    required property int index
                    width: pages.contentWidth
                    height: spreadPages.childrenRect.height
                    function pageItem(column) { return spreadRepeater.itemAt(column); }
                    Row {
                        id: spreadPages; anchors.horizontalCenter: parent.horizontalCenter; spacing: 16
                        Repeater {
                            id: spreadRepeater
                            model: Math.min(root.pageColumns,pdf.document.count-spreadRow.index*root.pageColumns)
                            delegate: DocumentPage {
                                required property int modelData
                                index: spreadRow.index*root.pageColumns+modelData
                            }
                        }
                    }
                }
            }
            ScrollInput {
                controller: root.pdf
                objectName: "pageScrollInput"; anchors.fill: parent; view: pages; visible: root.hasDocument
                onZoomRequested: function(amount) { root.zoomBy(amount); }
            }
            Flickable {
                id: startScreen; objectName: "startScreen"
                visible: !root.hasDocument; anchors.fill: parent; clip: true
                contentWidth: width; contentHeight: Math.max(height, startColumn.implicitHeight+80)
                boundsBehavior: Flickable.StopAtBounds
                readonly property var recentFiles: typeof library !== "undefined" && library.enabled ? library.recent : []
                ColumnLayout {
                    id: startColumn; width: Math.min(560, startScreen.width-48)
                    x: (startScreen.width-width)/2; y: Math.max(40,(startScreen.height-implicitHeight)/2-20); spacing: 0
                    Image { source: "../assets/icon.svg"; sourceSize: Qt.size(128,128); Layout.preferredWidth: 56; Layout.preferredHeight: 56; Layout.alignment: Qt.AlignHCenter; Layout.bottomMargin: 22 }
                    Text { text: "읽고, 다듬고, 하나로."; Layout.alignment: Qt.AlignHCenter; font.pixelSize: 28; font.weight: Font.DemiBold; color: Theme.ink }
                    Text { text: "필요한 도구만 가까이. 문서에 집중하는 시간."; Layout.alignment: Qt.AlignHCenter; Layout.topMargin: 10; font.pixelSize: 14; color: Theme.inkMuted }
                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter; spacing: 10; Layout.topMargin: 28
                        ActionButton { glyph: "open"; text: "PDF 열기"; primary: true; implicitWidth: 136; implicitHeight: 42; enabled: !pdf.busy; onClicked: pdf.chooseOpen() }
                        ActionButton { glyph: "merge"; text: "PDF 결합"; outlined: true; implicitWidth: 136; implicitHeight: 42; enabled: !pdf.busy; onClicked: pdf.showMerge() }
                    }
                    Text { text: "PDF를 이곳에 끌어 놓아도 열 수 있어요 · Ctrl+O"; Layout.alignment: Qt.AlignHCenter; Layout.topMargin: 14; font.pixelSize: 12; color: Theme.inkFaint }
                    RowLayout {
                        visible: startScreen.recentFiles.length>0; Layout.fillWidth: true; Layout.topMargin: 44; Layout.bottomMargin: 8
                        Text { text: "최근 문서"; font.pixelSize: 13; font.weight: Font.DemiBold; color: Theme.inkSoft; Layout.fillWidth: true }
                        ActionButton { objectName: "clearRecentButton"; compact: true; text: "목록 지우기"; onClicked: library.clear() }
                    }
                    Rectangle {
                        visible: startScreen.recentFiles.length>0
                        Layout.fillWidth: true; implicitHeight: recentColumn.implicitHeight+8; radius: Theme.radius+4
                        color: Theme.raised; border.color: Theme.line
                        Column {
                            id: recentColumn; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 4
                            Repeater {
                                model: startScreen.recentFiles
                                delegate: ItemDelegate {
                                    id: recentRow; required property var modelData; required property int index
                                    objectName: "recentFile"+index
                                    width: recentColumn.width; height: 52
                                    enabled: pdf && !pdf.busy
                                    ToolTip.visible: hovered; ToolTip.delay: 800; ToolTip.text: modelData.path
                                    background: Rectangle { radius: Theme.radius; color: recentRow.hovered ? Theme.hover : "transparent" }
                                    contentItem: RowLayout {
                                        spacing: 12
                                        Rectangle {
                                            Layout.preferredWidth: 30; Layout.preferredHeight: 36; radius: 3; color: Theme.dark ? "#2b322e" : "#f3f5f1"; border.color: Theme.lineStrong
                                            Text { anchors.centerIn: parent; text: "PDF"; font.pixelSize: 8; font.weight: Font.Bold; color: Theme.accentInk }
                                        }
                                        ColumnLayout {
                                            Layout.fillWidth: true; spacing: 2
                                            Text { Layout.fillWidth: true; text: recentRow.modelData.name; elide: Text.ElideMiddle; font.pixelSize: 13; font.weight: Font.Medium; color: recentRow.modelData.exists ? Theme.ink : Theme.inkMuted }
                                            Text {
                                                Layout.fillWidth: true; elide: Text.ElideLeft; font.pixelSize: 11; color: Theme.inkMuted
                                                text: !recentRow.modelData.exists ? "파일을 찾을 수 없어요 · " + recentRow.modelData.path
                                                    : (recentRow.modelData.page>0 ? (recentRow.modelData.page+1)+"페이지까지 읽음 · " : "") + recentRow.modelData.path
                                            }
                                        }
                                        ActionButton { glyph: "close"; compact: true; hint: "목록에서 빼기"; opacity: recentRow.hovered || hovered ? 1 : 0; onClicked: library.forget(recentRow.modelData.path) }
                                    }
                                    onClicked: root.tabWorkspace ? root.tabWorkspace.openRecent(modelData.path) : pdf.openPath(modelData.path)
                                }
                            }
                        }
                    }
                }
            }
            DropArea {
                enabled: root.tabActionsEnabled
                anchors.fill: parent
                onDropped: function(drop) { if (drop.hasUrls) { if(root.tabWorkspace) root.tabWorkspace.openPaths(drop.urls); else if(drop.urls.length) pdf.openPath(drop.urls[0]); } }
            }
        }
        ColumnLayout {
            id: commentsDock; objectName: "commentsDock"
            visible: (root.commentsOpen || annotationEditor.visible) && root.hasDocument
            Layout.preferredWidth: 350; Layout.minimumWidth: 300; Layout.maximumWidth: 350; Layout.fillWidth: false; Layout.fillHeight: true; spacing: 0
            CommentsPanel {
                id: commentsPanel
                controller: root.pdf; draft: annotationEditor; activeTool: root.tool; allowActions: !textDialog.visible
                Layout.fillWidth: true; Layout.fillHeight: true
                onToolRequested: function(tool) { if(tool==="closeComments") root.closeComments(); else root.useTool(tool); }
            }
        }
        Rectangle {
            visible: root.workspaceMode === "edit" && root.hasDocument
            Layout.preferredWidth: 218; Layout.fillHeight: true; color: Theme.surface
            Rectangle { width: 1; height: parent.height; color: Theme.line }
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 16; spacing: 7
                Text { text: "편집 도구"; font.pixelSize: 16; font.weight: Font.DemiBold; color: Theme.ink; Layout.bottomMargin: 12 }
                Text { text: "내용"; font.pixelSize: 11; color: Theme.inkMuted }
                ActionButton { objectName: "editTextButton"; Layout.fillWidth: true; leftAligned: true; glyph: "edit"; text: "본문 수정"; active: root.tool === "editText"; enabled: root.canEdit; onClicked: root.useTool("editText") }
                ActionButton { Layout.fillWidth: true; leftAligned: true; glyph: "text"; text: "텍스트 추가"; active: root.tool === "addText"; enabled: root.canEdit; onClicked: root.useTool("addText") }
                ActionButton { Layout.fillWidth: true; leftAligned: true; glyph: "image"; objectName: "insertImageButton"; text: "이미지 삽입"; active: false; enabled: root.canEdit; onClicked: { root.useTool("imageMove"); pdf.chooseImage(); } }
                ActionButton { objectName: "moveImageButton"; Layout.fillWidth: true; leftAligned: true; glyph: "hand"; text: "이미지 이동·크기"; active: root.tool==="imageMove"; enabled: root.canEdit; onClicked: root.useTool("imageMove") }
                Text { text: "주석"; font.pixelSize: 11; color: Theme.inkMuted; Layout.topMargin: 18 }
                ActionButton { Layout.fillWidth: true; leftAligned: true; glyph: "highlight"; text: "형광펜"; active: root.tool === "highlight"; enabled: root.canAnnotate; onClicked: root.useTool("highlight") }
                ActionButton { Layout.fillWidth: true; leftAligned: true; glyph: "note"; text: "메모"; active: root.tool === "note"; enabled: root.canAnnotate; onClicked: root.useTool("note") }
                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.line; Layout.topMargin: 15; Layout.bottomMargin: 10 }
                ActionButton { Layout.fillWidth: true; leftAligned: true; glyph: "undo"; text: "되돌리기"; hint: "Ctrl+Z"; enabled: (root.canEdit || root.canAnnotate) && pdf.document.canUndo; onClicked: pdf.undo() }
                ActionButton { Layout.fillWidth: true; leftAligned: true; glyph: "redo"; text: "다시 실행"; hint: "Ctrl+Shift+Z"; enabled: (root.canEdit || root.canAnnotate) && pdf.document.canRedo; onClicked: pdf.redo() }
                Item { Layout.fillHeight: true }
                Text { Layout.fillWidth: true; text: "저장하면 변경 사항이 PDF에 반영됩니다."; wrapMode: Text.WordWrap; font.pixelSize: 12; color: Theme.inkMuted }
            }
        }
    }

    footer: Rectangle {
        objectName: "readerFooter"; visible: !root.presenting
        height: 34; color: Theme.surface
        Rectangle { width: parent.width; height: 1; color: Theme.line }
        RowLayout {
            anchors.fill: parent; anchors.leftMargin: 15; anchors.rightMargin: 15; spacing: 9
            BusyIndicator { running: pdf.busy || pdf.ocrBusy; visible: running; Layout.preferredWidth: 22; Layout.preferredHeight: 22 }
            Text { text: pdf.ocrBusy ? pdf.ocrProgress : pdf.status; elide: Text.ElideRight; Layout.fillWidth: true; color: Theme.inkMuted; font.pixelSize: 12 }
            ActionButton { visible: pdf.ocrBusy; text: "OCR 취소"; implicitHeight: 28; onClicked: pdf.cancelOcr() }
            RowLayout {
                visible: root.hasDocument; spacing: 5
                ActionButton { glyph: "left"; hint: "이전 페이지 · ← / ↑ / Page Up"; compact: true; enabled: pdf.currentPage>0; onClicked: root.turnPage(-1) }
                TextField { id: pageInput; objectName: "pageNumberInput"; text: pdf.currentPage+1; Layout.preferredWidth: 50; Layout.preferredHeight: 26; horizontalAlignment: Text.AlignHCenter; font.pixelSize: 12; selectByMouse: true; color: Theme.ink
                    background: Rectangle { radius: Theme.radiusSmall; color: Theme.field; border.color: pageInput.activeFocus ? Theme.focusRing : Theme.lineStrong } validator: IntValidator { bottom: 1; top: Math.max(1,pdf.document.count) } onAccepted: { root.goPage(parseInt(text)-1); pages.forceActiveFocus(); } }
                Text { text: "/ " + pdf.document.count; color: Theme.inkMuted; font.pixelSize: 12 }
                ActionButton { glyph: "right"; hint: "다음 페이지 · → / ↓ / Page Down / Space"; compact: true; enabled: pdf.currentPage<pdf.document.count-1; onClicked: root.turnPage(1) }
            }
        }
    }

    AnnotationEditor { id: annotationEditor; controller: root.pdf }

    component CommentMark: Item {
        property var annotation: null
        property int page: -1
        property real factor: 1
        property bool strong: false
        readonly property bool shown: !!annotation && annotation.page===page && !!annotation.rect
        enabled: false
        Repeater {
            model: parent.shown ? (parent.annotation.regions && parent.annotation.regions.length ? parent.annotation.regions : [parent.annotation.rect]) : []
            delegate: Rectangle {
                required property var modelData
                readonly property real f: parent.factor
                x: modelData[0]*f-3; y: modelData[1]*f-3
                width: (modelData[2]-modelData[0])*f+6; height: (modelData[3]-modelData[1])*f+6
                radius: 3; color: parent.strong ? "#262e5c4d" : "transparent"
                border.color: parent.strong ? Theme.accent : Theme.focusRing; border.width: parent.strong ? 2 : 1
            }
        }
    }

    component DocumentPage: Item {
                    id: pageCell
                    required property int index
                    width: pageWidth
                    height: paper.height + 21
                    property real pageWidth: Math.max(80, ((pages.width-64-16*(root.pageColumns-1))/root.pageColumns)*root.zoom)
                    property real ratio: pdf.pageRatio(index)
                    property real pdfWidth: pdf.pageWidth(index)
                    property var pageBlocks: { pdf.blocksTick; return root.tool === "editText" ? pdf.blockBoxes(index) : []; }
                    property bool near: !root.presenting && parent.parent.y+height >= pages.contentY-pages.height && parent.parent.y <= pages.contentY+pages.height*2
                    property string imageUrl: ""
                    property string renderError: ""
                    function request() {
                        imageUrl=pdf.imageUrl(index,"main");renderError=pdf.imageError(index,"main");ratio=pdf.pageRatio(index);pdfWidth=pdf.pageWidth(index);
                        if (near) { pdf.requestPage(index,"main",Math.ceil(pageWidth*Screen.devicePixelRatio)); pdf.requestText(index); if(root.tool==="editText") pdf.loadBlocksForPage(index); }
                        else pdf.releasePage(index,"main");
                    }
                    onNearChanged: request()
                    Connections { target: root; function onToolChanged(){if(root.tool==="editText" && pageCell.near) pdf.loadBlocksForPage(pageCell.index);} }
                    onPageWidthChanged: renderDelay.restart()
                    Component.onCompleted: request()
                    Timer { id: renderDelay; interval: 100; onTriggered: pageCell.request() }
                    Connections {
                        target: root.pdf
                        function onStateChanged() { pageCell.request(); }
                        function onPageImageChanged(page,kind) { if(page===pageCell.index && kind==="main") { pageCell.imageUrl=pdf.imageUrl(page,kind);pageCell.renderError=pdf.imageError(page,kind); } }
                        function onPageMetricsChanged(page) { if(page===pageCell.index) { pageCell.ratio=pdf.pageRatio(page);pageCell.pdfWidth=pdf.pageWidth(page); } }
                    }
                    Timer { interval: 700; repeat: true; running: pageCell.near && !pageCell.imageUrl && !pageCell.renderError; onTriggered: pageCell.request() }
                    // Soft two-step shadow gives the page some depth without a heavy frame.
                    Rectangle { anchors.horizontalCenter: parent.horizontalCenter; y: 1; width: paper.width+6; height: paper.height+6; radius: 4; color: Theme.dark ? "#30000000" : "#0c1a2a1f" }
                    Rectangle { anchors.horizontalCenter: parent.horizontalCenter; y: 1; width: paper.width+2; height: paper.height+3; radius: 2; color: Theme.dark ? "#50000000" : "#161a2a1f" }
                    Rectangle {
                        id: paper; objectName: "paper" + pageCell.index
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: pageCell.pageWidth; height: width * pageCell.ratio
                        color: "white"; border.width: Theme.dark ? 0 : 1; border.color: Theme.pageEdge
                        Image { anchors.fill: parent; anchors.margins: 1; source: pageCell.imageUrl; fillMode: Image.Stretch; cache: false; asynchronous: true; retainWhileLoading: true; smooth: true }
                        Text { visible: pageCell.imageUrl === ""; anchors.centerIn: parent; text: pageCell.renderError ? "페이지를 표시하지 못했어요." : "페이지 불러오는 중…"; color: "#8a938b"; font.pixelSize: 14 }
                        ActionButton { anchors.centerIn: parent; anchors.verticalCenterOffset: 40; visible: !pageCell.imageUrl && !!pageCell.renderError; text: "다시 불러오기"; outlined: true; z: 20; hint: pageCell.renderError; onClicked: pdf.retryPage(pageCell.index,"main",Math.ceil(pageCell.pageWidth*Screen.devicePixelRatio)) }
                        Repeater {
                            model: root.tool === "editText" && !textDialog.visible ? pageCell.pageBlocks : []
                            delegate: Rectangle {
                                required property var modelData
                                objectName: "textBlock"+pageCell.index+"_"+modelData.id
                                property real scale: paper.width/pageCell.pdfWidth
                                x: modelData.displayRect[0]*scale; y: modelData.displayRect[1]*scale
                                width: (modelData.displayRect[2]-modelData.displayRect[0])*scale
                                height: (modelData.displayRect[3]-modelData.displayRect[1])*scale
                                color: blockMouse.containsMouse ? "#194b7851" : "transparent"
                                border.color: "#8da689"; border.width: 1; radius: 2
                                MouseArea { id: blockMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.IBeamCursor; enabled: root.canEdit; onClicked: pdf.editBlock(parent.modelData) }
                            }
                        }
                        Repeater {
                            model: pdf.searchResults
                            delegate: Item {
                                required property var modelData
                                anchors.fill: parent
                                Repeater {
                                    model: modelData.page === pageCell.index ? modelData.rects : []
                                    delegate: Rectangle {
                                        required property var modelData
                                        property real scale: paper.width/pageCell.pdfWidth
                                        x: modelData[0]*scale; y: modelData[1]*scale
                                        width: (modelData[2]-modelData[0])*scale; height: (modelData[3]-modelData[1])*scale
                                        color: "#66ffcf32"; border.color: "#dba914"; radius: 1
                                    }
                                }
                            }
                        }
                        Rectangle {
                            property var hit: pdf.activeSearchHit
                            property real factor: paper.width/pageCell.pdfWidth
                            visible: hit.page===pageCell.index && !!hit.rect
                            x: hit.rect ? hit.rect[0]*factor-2 : 0; y: hit.rect ? hit.rect[1]*factor-2 : 0
                            width: hit.rect ? (hit.rect[2]-hit.rect[0])*factor+4 : 0
                            height: hit.rect ? (hit.rect[3]-hit.rect[1])*factor+4 : 0
                            color: "#66ed9a42"; border.color: "#bd7330"; border.width: 2; radius: 2
                        }
                        // The chosen comment stands out on the page; the card under the
                        // pointer in the list is outlined more lightly.
                        CommentMark { objectName: "selectedMark"+pageCell.index; anchors.fill: parent; z: 40; annotation: pdf.selectedAnnotation; page: pageCell.index; factor: paper.width/pageCell.pdfWidth; strong: true; visible: root.commentsOpen }
                        CommentMark { anchors.fill: parent; z: 40; annotation: commentsPanel.hoveredItem; page: pageCell.index; factor: paper.width/pageCell.pdfWidth; visible: root.commentsOpen }
                        TextLayer {
                            controller: root.pdf
                            allowEdits: !textDialog.visible && !annotationEditor.visible
                            onMenuOpenChanged: root.readerMenuOpen=menuOpen
                            anchors.fill: parent; pageNumber: pageCell.index; pdfWidth: pageCell.pdfWidth; viewport: pages
                            markupTool: root.isMarkupTool(root.tool) ? root.tool : ""
                            visible: root.tool === "read" || !!markupTool; enabled: visible && !pdf.busy
                        }
                        MouseArea {
                            // Below the live editor (z 60): any click elsewhere on the page commits.
                            objectName: "commitCatcher"+pageCell.index
                            anchors.fill: parent; z: 55; enabled: textDialog.visible
                            cursorShape: root.tool==="editText" ? Qt.IBeamCursor : Qt.ArrowCursor
                            onPressed: function(mouse) {
                                var s=pageCell.pdfWidth/paper.width;
                                root.commitEdit(root.tool==="editText" ? {page:pageCell.index,x:mouse.x*s,y:mouse.y*s} : null);
                            }
                        }
                        InlineTextEditor { session: textDialog; controller: root.pdf; pageNumber: pageCell.index; factor: paper.width/pageCell.pdfWidth }
                        LegacyTextEditor { session: textDialog; controller: root.pdf; pageNumber: pageCell.index; factor: paper.width/pageCell.pdfWidth }
                        ImageHandles {
                            anchors.fill: parent; z: 50; controller: root.pdf
                            objects: { pdf.textTick; return root.tool === "imageMove" ? pdf.movableImages(pageCell.index) : []; }
                            factor: paper.width/pageCell.pdfWidth; pdfWidth: pageCell.pdfWidth; pdfHeight: pageCell.pdfWidth*pageCell.ratio
                            editing: root.tool==="imageMove" && root.canEdit
                        }
                        HoverHandler { enabled: root.tool === "hand"; cursorShape: Qt.OpenHandCursor }
                        MouseArea {
                            id: region; anchors.fill: parent
                            enabled: (root.canEdit && ["addText", "image"].indexOf(root.tool)>=0) || (root.canAnnotate && root.tool==="note")
                            cursorShape: root.tool === "read" ? Qt.IBeamCursor : Qt.CrossCursor
                            property point start: Qt.point(0,0)
                            property point end: Qt.point(0,0)
                            onPressed: function(mouse) { start = Qt.point(mouse.x,mouse.y); end=start; }
                            onPositionChanged: function(mouse) { if (pressed) end = Qt.point(mouse.x,mouse.y); }
                            onReleased: function(mouse) {
                                end = Qt.point(mouse.x,mouse.y);
                                var s = pageCell.pdfWidth/paper.width;
                                var r = [Math.min(start.x,end.x)*s, Math.min(start.y,end.y)*s, Math.max(start.x,end.x)*s, Math.max(start.y,end.y)*s];
                                if (root.tool==="note" || (r[2]-r[0] > 3 && r[3]-r[1] > 3)) pdf.regionAction(pageCell.index, r, root.tool);
                            }
                        }
                        Rectangle {
                            visible: region.pressed; x: Math.min(region.start.x,region.end.x); y: Math.min(region.start.y,region.end.y)
                            width: Math.abs(region.start.x-region.end.x); height: Math.abs(region.start.y-region.end.y)
                            border.color: "#51765a"; color: "#224b7851"; border.width: 1
                        }
                    }
                    Text { anchors.horizontalCenter: parent.horizontalCenter; y: paper.height+5; text: pageCell.index+1; font.pixelSize: 11; color: Theme.inkMuted }
                }

    Loader {
        id: presentation; anchors.fill: parent; z: 100
        active: root.presenting; visible: active
        sourceComponent: PresentationView {
            controller: root.pdf
            onPageRequested: function(page) { root.goPage(page); }
            onExitRequested: root.endPresentation()
        }
        onLoaded: item.forceActiveFocus()
    }

    Connections {
        target: root.tabWorkspace
        function onAboutToSwitch() { root.saveView(); }
        function onActiveChanged() { root.restoreView(); }
        function onCloseApproved() { root.quitApplication(); }
        function onShowError(message) { errorDialog.message=message; errorDialog.open(); }
    }
    Timer {
        id: navigationTimer; interval: 35; repeat: true
        onTriggered: {
            var nav=root.pendingNavigation;
            if(!nav || nav.owner!==root.pdf) { stop(); root.restoring=false; return; }
            pages.forceLayout();
            var cell=root.cellForPage(nav.page);
            if(!cell) pages.positionViewAtIndex(root.rowForPage(nav.page),ListView.Beginning);
            else {
                var minY=pages.originY-pages.topMargin;
                var maxY=Math.max(minY,pages.originY+pages.contentHeight-pages.height+pages.bottomMargin);
                var y=nav.offset!==undefined ? root.cellTop(cell)+nav.offset*cell.pageWidth : root.cellTop(cell)+nav.y*cell.pageWidth/cell.pdfWidth-pages.height*.25;
                pages.contentY=Math.max(minY,Math.min(maxY,y));
                if(nav.horizontal!==undefined) pages.contentX=nav.horizontal*pages.contentWidth;
                else {
                    var x=cell.mapToItem(pages.contentItem,0,0).x+nav.x*cell.pageWidth/cell.pdfWidth;
                    if(x<pages.contentX+24 || x>pages.contentX+pages.width-80) pages.contentX=Math.max(0,Math.min(pages.contentWidth-pages.width,x-pages.width*.25));
                }
                pdf.setCurrentPage(nav.page);
            }
            nav.tries++;
            if(nav.tries>=12 || (cell && cell.imageUrl && nav.tries>=3)) { stop(); root.pendingNavigation=null; root.restoring=false; }
        }
    }
    Timer { id: searchDelay; interval: 300; onTriggered: pdf.search(root.pendingQuery) }
    Timer {
        interval: 35; repeat: true; running: root.draggedPage >= 0
        onTriggered: {
            var step = root.dragViewportY < 40 ? -12 : root.dragViewportY > thumbs.height-40 ? 12 : 0;
            if (step === 0) return;
            thumbs.contentY = Math.max(0, Math.min(thumbs.contentHeight-thumbs.height, thumbs.contentY+step));
            var index = thumbs.indexAt(thumbs.width/2, thumbs.contentY+root.dragViewportY);
            if (index >= 0) { var cell=thumbs.itemAtIndex(index); root.dropIndex=index+(cell && thumbs.contentY+root.dragViewportY>cell.y+cell.height/2 ? 1 : 0); }
        }
    }
    Connections {
        target: root.pdf
        function onOpenMergeDialog() { mergeDialog.open(); }
        function onOpenComments() { root.commentsOpen=true; }
        function onShowAnnotationEditor(data) { annotationEditor.compose(data); }
        function onNavigateRequested(page,x,y) { root.jumpTo(page,x,y); }
        function onResumeRequested(page) { root.goPage(page); }
        function onOutlineRequested(page,y) { root.jumpToHeading(page,y); }
        function onTextCommitted() { textDialog.close(); root.finishDraftClose(); Qt.callLater(root.openPendingEdit); }
        function onBlocksChanged() { if(root.pendingEditPoint) Qt.callLater(root.openPendingEdit); }
        function onAnnotationCommitted() { annotationEditor.close(); if(root.tool==="note") root.tool="read"; root.finishDraftClose(); }
        function onImageInserted() { root.useTool("imageMove"); }
        function onShowTextEditor(data) { textDialog.compose(data); }
        function onShowError(message) { root.closeAfterEdit=false; if(!root.tabWorkspace) { errorDialog.message = message; errorDialog.open(); } }
        function onStateChanged() {
            if (!root.presenting && root.tool === "editText" && root.hasDocument && !pdf.busy) pdf.loadBlocks(pdf.currentPage);
        }
        function onSelectionChanged() {
            if(root.sidebarOpen) thumbs.positionViewAtIndex(pdf.currentPage,ListView.Contain);
            if (!root.presenting && root.tool === "editText" && root.hasDocument) pdf.loadBlocks(pdf.currentPage);
        }
    }

    MergeDialog { id: mergeDialog; controller: root.pdf }

    Connections { target: pdf.liveEditor; function onApplyFailed(){root.closeAfterEdit=false;} }
    property bool closeAfterEdit: false
    function finishDraftClose() {
        if(!closeAfterEdit)return;
        closeAfterEdit=false; Qt.callLater(function(){root.close();});
    }
    Dialog {
        id: draftClose; objectName: "draftCloseDialog"; anchors.centerIn: parent
        title: "편집 중인 내용"; width: 510; modal: true; closePolicy: Popup.NoAutoClose
        contentItem: ColumnLayout {
            spacing: 18
            Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "아직 적용하지 않은 편집 내용이 있어요. 어떻게 닫을까요?" }
            Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.warnInk; visible: textDialog.visible && !pdf.liveEditor.canApply && textDialog.targetData.mode==="replace"; text: "글꼴 확인이나 오류 해결 전에는 적용할 수 없어요. 편집으로 돌아가거나 이번 입력을 버리고 닫을 수 있어요." }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                ActionButton { objectName: "continueEditing"; text: "계속 편집"; onClicked: {root.closeAfterEdit=false;root.closeAllRequested=false;draftClose.close();} }
                ActionButton { objectName: "discardDraftClose"; text: "입력 버리고 닫기"; enabled: !pdf.busy; onClicked: {root.closeAfterEdit=false;draftClose.close();textDialog.close();annotationEditor.close();Qt.callLater(function(){root.close();});} }
                ActionButton { objectName: "applyDraftClose"; text: "적용 후 닫기"; primary: true; enabled: !pdf.busy && (textDialog.visible ? (textDialog.targetData.mode!=="replace" || pdf.liveEditor.canApply) : annotationEditor.canApply); onClicked: {root.closeAfterEdit=true;draftClose.close();if(textDialog.visible)pdf.applyText(textDialog.targetData,textDialog.text,textDialog.fontSize,textDialog.areaHeight);else annotationEditor.apply();} }
            }
        }
    }

    QtObject {
        id: textDialog; objectName: "textEditorSession"
        property bool visible: false
        property var targetData: ({})
        property string text: ""
        property real fontSize: 14
        property real areaHeight: 40
        property string fallbackFont: root.uiFontFamily
        onVisibleChanged: { pdf.setTextEditorVisible(visible); if(!visible) root.commitWhenReady=false; }
        function close() { visible=false; }
        function compose(data) {
            if(visible) return;
            targetData=data; text=data.text || ""; fontSize=Number(data.size || 14);
            areaHeight=data.mode==="replace" ? data.rect[3]-data.rect[1]+10 : data.height;
            visible=true;
        }
    }

    Dialog {
        id: ocrDialog; anchors.centerIn: parent; width: 510; modal: true; title: "문자 인식 · OCR"
        standardButtons: Dialog.NoButton
        contentItem: ColumnLayout {
            spacing: 15
            Text { Layout.fillWidth: true; text: "스캔 페이지에 검색 가능한 문자층을 추가해요. 이미 텍스트가 있는 페이지는 건너뛰며, 원본 이미지는 유지합니다."; wrapMode: Text.WordWrap; color: Theme.inkSoft }
            Text { Layout.fillWidth: true; visible: pdf.languages.length === 0; text: "OCR 언어 데이터를 찾지 못했어요. 설치 프로그램으로 다시 설치해 주세요."; wrapMode: Text.WordWrap; color: Theme.warnInk }
            Text { text: "인식 범위"; font.weight: Font.DemiBold; color: Theme.ink }
            ComboBox { id: ocrScope; Layout.fillWidth: true; model: ["현재 페이지", "선택한 페이지", "전체 문서"] }
            Text { text: "인식 언어"; font.weight: Font.DemiBold; color: Theme.ink }
            ComboBox {
                id: ocrLanguage; Layout.fillWidth: true
                model: pdf.languages.indexOf("kor")>=0 && pdf.languages.indexOf("eng")>=0 ? ["kor+eng"].concat(pdf.languages.filter(function(x){return x!=="osd";})) : pdf.languages.filter(function(x){return x!=="osd";})
            }
            Text { visible: pdf.languages.length > 0 && pdf.languages.indexOf("kor") < 0; text: "한국어 데이터(kor)가 아직 설치되어 있지 않아요."; color: Theme.warnInk; font.pixelSize: 13 }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                ActionButton { text: "취소"; onClicked: ocrDialog.close() }
                ActionButton { text: "OCR 시작"; primary: true; enabled: ocrLanguage.count>0; onClicked: { pdf.startOcr(["current","selected","all"][ocrScope.currentIndex],ocrLanguage.currentText); ocrDialog.close(); } }
            }
        }
    }

    Dialog {
        id: settingsDialog; objectName: "settingsDialog"; parent: Overlay.overlay; anchors.centerIn: parent; width: 490; modal: true; title: "설정"
        standardButtons: Dialog.Ok
        contentItem: ScrollView {
            id: settingsScroll; objectName: "settingsScroll"; clip: true
            implicitHeight: Math.min(settingsContent.implicitHeight, Math.max(200, root.height - 170))
            contentWidth: availableWidth
            contentHeight: settingsContent.implicitHeight
            ColumnLayout {
                id: settingsContent; width: settingsScroll.availableWidth
                spacing: 14
                ColumnLayout {
                    objectName: "defaultAppsSection"; Layout.fillWidth: true; visible: Qt.platform.os === "windows"; spacing: 6
                    ActionButton { objectName: "defaultAppsButton"; text: "기본 PDF 앱 설정"; onClicked: { settingsDialog.close(); pdf.openDefaultAppsSettings(); } }
                    Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "Windows 설정에서 .pdf의 앱을 윤DF로 선택하면 PDF를 더블클릭해 열 수 있어요."; color: Theme.inkMuted; font.pixelSize: 13 }
                }
                Text { text: "화면 테마"; color: Theme.ink }
                ComboBox {
                    objectName: "themeChoice"; Layout.fillWidth: true
                    model: ["Windows 설정 따르기","밝게","어둡게"]
                    currentIndex: ["system","light","dark"].indexOf(pdf.themeMode)
                    onActivated: pdf.setThemeMode(["system","light","dark"][currentIndex])
                }
                Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "어두운 테마에서도 PDF 페이지는 원래 색 그대로 보여요."; color: Theme.inkMuted; font.pixelSize: 12; Layout.bottomMargin: 6 }
                CheckBox {
                    visible: typeof library !== "undefined"; text: "최근 문서와 읽던 페이지 기억"
                    checked: typeof library !== "undefined" && library.enabled
                    onToggled: library.setEnabled(checked)
                }
                Text { visible: typeof library !== "undefined"; Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "다시 열면 지난번에 보던 페이지로 이동해요. 기록은 이 컴퓨터에만 저장돼요. 끄면 목록도 지워져요."; color: Theme.inkMuted; font.pixelSize: 12; Layout.bottomMargin: 6 }
                Text { text: "마우스 휠 속도  ·  " + pdf.wheelSpeed.toFixed(1) + "배"; color: Theme.ink }
                Slider { Layout.fillWidth: true; from: .5; to: 5; stepSize: .1; value: pdf.wheelSpeed; onMoved: pdf.setWheelSpeed(value) }
                Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "Windows의 휠 줄 수 설정에 배율을 적용합니다. 무한 휠의 입력량을 모두 반영하며 터치패드의 픽셀 이동은 그대로 유지합니다."; color: Theme.inkMuted; font.pixelSize: 13 }
                ActionButton { text: "기본 속도 (1배)"; onClicked: pdf.setWheelSpeed(1) }
                Text { text: "페이지 이미지 캐시"; color: Theme.ink; Layout.topMargin: 8 }
                ComboBox { Layout.fillWidth: true; model: ["256 MB · 절약","512 MB · 권장","1 GB · 많은 페이지 재사용"]; currentIndex: pdf.cacheMiB>=1024 ? 2 : pdf.cacheMiB>=512 ? 1 : 0; onActivated: pdf.setCacheMiB([256,512,1024][currentIndex]) }
                Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "한번 본 페이지를 메모리에 보관해 다시 열 때 빠르게 표시합니다. 미리보기·PDF 엔진·그래픽 메모리는 별도로 사용합니다."; color: Theme.inkMuted; font.pixelSize: 12 }
                ComboBox { Layout.fillWidth: true; model: ["그래픽 가속 · 자동","호환 모드 · 화면 표시 문제가 있을 때"]; currentIndex: pdf.graphicsMode === "software" ? 1 : 0; onActivated: pdf.setGraphicsMode(currentIndex ? "software" : "auto") }
                Text { text: "그래픽 설정은 앱을 다시 실행하면 적용됩니다."; color: Theme.inkMuted; font.pixelSize: 12 }
                CheckBox { text: "현재 보는 스캔 페이지 자동 OCR"; checked: pdf.automaticOcr; onToggled: pdf.setAutomaticOcr(checked) }
                Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "일반 PDF의 글자는 바로 선택할 수 있습니다. 스캔은 인식이 끝나면 선택할 수 있으며, 저장하면 문자층이 PDF에 남습니다."; color: Theme.inkMuted; font.pixelSize: 13 }
                ActionButton { text: "오류 로그 폴더 열기"; onClicked: pdf.openLogFolder() }
            }
        }
    }

    Dialog {
        id: aboutDialog; anchors.centerIn: parent; width: 650; height: 570; modal: true; title: "윤DF · " + Qt.application.version
        standardButtons: Dialog.Ok
        contentItem: ColumnLayout {
            Text { text: "Copyright © 2026 YoonDF contributors"; color: Theme.ink }
            Text { text: "AGPL-3.0-or-later · 이 라이선스에 따라 수정·재배포할 수 있습니다.\n보증 없이 제공됩니다. 전체 소스와 빌드 스크립트는 배포 압축파일에 포함됩니다."; wrapMode: Text.WordWrap; Layout.fillWidth: true; color: Theme.inkSoft; font.pixelSize: 13 }
            ScrollView {
                Layout.fillWidth: true; Layout.fillHeight: true
                TextArea { readOnly: true; selectByMouse: true; text: aboutDialog.visible ? pdf.licenseText() : ""; wrapMode: TextEdit.Wrap; font.pixelSize: 12 }
            }
        }
    }

    Dialog {
        id: errorDialog; anchors.centerIn: parent; width: 520; modal: true; title: "확인해 주세요"
        property string message: ""
        standardButtons: Dialog.Ok
        contentItem: Text { text: errorDialog.message; wrapMode: Text.WordWrap; color: Theme.ink; font.pixelSize: 14 }
    }
}
