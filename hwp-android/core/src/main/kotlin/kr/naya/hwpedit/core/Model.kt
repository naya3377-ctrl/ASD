package kr.naya.hwpedit.core

/*
 * 화면에 보여 줄 문서 모델.
 *
 * hwp·hwpx 어느 쪽이든 같은 모양으로 바꿔서 앱에 넘긴다. 앱은 이 모델만 보고 화면을 그리고,
 * 사용자가 고친 글은 TextFlowBlock 의 flowId 와 새 글자열로만 돌려준다.
 *
 * 글자열 안의 특수 문자:
 *   '\n'      문단 구분 (TextFlowBlock.text 에서만 쓰임)
 *   '\t'      탭
 *   '\u2028'  문단 안 줄 바꿈 (한글의 Shift+Enter)
 *   '\u00A0'  묶음 빈칸
 *   '\u2007'  고정폭 빈칸
 *   '\u2011'  하이픈(한글 문서의 하이픈 문자)
 */

enum class DocFormat(val extension: String, val mimeType: String) {
    HWP("hwp", "application/x-hwp"),
    HWPX("hwpx", "application/hwp+zip"),
}

object SpecialChars {
    const val LINE_BREAK = '\u2028'
    const val NB_SPACE = '\u00A0'
    const val FW_SPACE = '\u2007'
    const val HYPHEN = '\u2011'
    const val TAB = '\t'
    const val PARA_BREAK = '\n'

    /** 앱에서 입력·붙여넣기한 글자 중 문서에 쓸 수 없는 제어 문자를 정리한다. */
    fun sanitize(text: String): String {
        val sb = StringBuilder(text.length)
        var i = 0
        while (i < text.length) {
            val c = text[i]
            when {
                c == '\r' -> {
                    // \r\n 은 문단 하나로, 홀로 쓰인 \r 은 문단 구분으로 본다.
                    if (i + 1 < text.length && text[i + 1] == '\n') {
                        // \n 이 다음에 처리된다.
                    } else {
                        sb.append('\n')
                    }
                }
                c == '\n' || c == '\t' -> sb.append(c)
                c < ' ' -> sb.append(' ')
                c == '\u2029' -> sb.append('\n')
                c == '\uFFFC' || c == '\uFFFE' || c == '\uFFFF' -> {}
                else -> sb.append(c)
            }
            i++
        }
        return sb.toString()
    }
}

class DocModel(
    val format: DocFormat,
    val blocks: List<Block>,
    /** 본문 폭(HWPUNIT, 1/7200인치). 표·그림 크기를 화면 폭에 맞출 때 쓴다. */
    val bodyWidth: Long,
    /** 열 수는 있지만 저장하면 안 되는 문서(배포용 문서 등)일 때 이유. */
    val readOnlyReason: String?,
    val warnings: List<String>,
) {
    /**
     * 모든 편집 가능한 글 흐름을 문서 순서대로 돌려준다.
     * 순서: 블록 차례대로, 표는 칸들 다음 캡션, 그림은 캡션, 상자는 안쪽 블록.
     * 앱이 화면을 만드는 순서도 이와 같다.
     */
    fun allFlows(): List<TextFlowBlock> {
        val out = ArrayList<TextFlowBlock>()
        fun walk(blocks: List<Block>) {
            for (b in blocks) when (b) {
                is TextFlowBlock -> out.add(b)
                is TableBlock -> {
                    b.cells.forEach { walk(it.blocks) }
                    walk(b.caption)
                }
                is ImageBlock -> walk(b.caption)
                is BoxBlock -> walk(b.blocks)
                is ObjectBlock -> {}
            }
        }
        walk(blocks)
        return out
    }

    /** 문서 전체 글자(검색·확인용). */
    fun plainText(): String = allFlows().joinToString("\n") { it.text }
}

sealed interface Block

/** 연달아 있는 문단 묶음. 앱에서는 입력칸 하나로 보여 주고 통째로 고친다. */
class TextFlowBlock(
    val flowId: Int,
    val paragraphs: List<ParaView>,
) : Block {
    val text: String by lazy { paragraphs.joinToString("\n") { it.text } }
}

class ParaView(
    val text: String,
    val runs: List<StyledRun>,
    val style: ParaStyle,
)

/** [start, end) 범위의 글자 모양. */
class StyledRun(val start: Int, val end: Int, val style: CharStyle)

data class CharStyle(
    val bold: Boolean = false,
    val italic: Boolean = false,
    val underline: Boolean = false,
    val strike: Boolean = false,
    val superscript: Boolean = false,
    val subscript: Boolean = false,
    /** 글자 크기(포인트). */
    val sizePt: Float = 10f,
    /** 글자 색 0xAARRGGBB. */
    val color: Int = 0xFF000000.toInt(),
    /** 한글 글꼴 이름(예: 함초롬바탕). */
    val fontName: String? = null,
) {
    companion object {
        val DEFAULT = CharStyle()
    }
}

enum class Align { JUSTIFY, LEFT, RIGHT, CENTER, DISTRIBUTE }

data class ParaStyle(
    val align: Align = Align.JUSTIFY,
    /** 왼쪽 여백(포인트). */
    val marginLeftPt: Float = 0f,
    val marginRightPt: Float = 0f,
    /** 첫 줄 들여쓰기(+) / 내어쓰기(-) (포인트). */
    val indentPt: Float = 0f,
    val spaceBeforePt: Float = 0f,
    val spaceAfterPt: Float = 0f,
    /** 줄 간격(%). 비율 방식이 아니면 null. */
    val lineSpacingPercent: Int? = 160,
) {
    companion object {
        val DEFAULT = ParaStyle()
    }
}

class TableBlock(
    val rowCount: Int,
    val colCount: Int,
    /** 각 열의 폭(HWPUNIT). */
    val columnWidths: List<Long>,
    val cells: List<CellView>,
    /** 표 캡션 등 표에 딸린 글. */
    val caption: List<Block>,
) : Block

class CellView(
    val row: Int,
    val col: Int,
    val rowSpan: Int,
    val colSpan: Int,
    val blocks: List<Block>,
)

class ImageBlock(
    /** 그림 파일 내용(png/jpg/gif/bmp 등). 찾지 못했으면 null. */
    val data: ByteArray?,
    /** 문서에 놓인 크기(HWPUNIT). 모르면 0. */
    val width: Long,
    val height: Long,
    val caption: List<Block>,
) : Block

/** 글상자, 머리말·꼬리말, 각주처럼 따로 글을 품고 있는 개체. */
class BoxBlock(
    val kind: BoxKind,
    val label: String,
    val blocks: List<Block>,
) : Block

enum class BoxKind { TEXT_BOX, HEADER, FOOTER, FOOTNOTE, ENDNOTE, GROUP }

/** 아직 보여 줄 수 없는 개체(수식, 도형, 차트 등). 문서에는 그대로 남는다. */
class ObjectBlock(val label: String, val detail: String? = null) : Block
