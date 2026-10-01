package kr.naya.hwpedit.core

import java.io.File

object TestSupport {
    fun sample(name: String): ByteArray =
        TestSupport::class.java.getResourceAsStream("/samples/$name")?.readBytes()
            ?: error("missing sample $name")

    val sampleNames: List<String> = listOf(
        "blank.hwp", "text.hwp", "table.hwp", "picture.hwp", "textbox.hwp", "footnote.hwp",
        "headerfooter.hwp", "field.hwp", "merged-cells.hwp",
        "blank.hwpx", "table.hwpx", "picture.hwpx", "sample1.hwpx", "headerfooter.hwpx",
    )

    fun output(name: String, bytes: ByteArray) {
        val dir = System.getProperty("hwp.testOutput") ?: return
        File(dir).mkdirs()
        File(dir, name).writeBytes(bytes)
    }

    fun dump(model: DocModel): String {
        val sb = StringBuilder()
        fun line(depth: Int, s: String) {
            repeat(depth) { sb.append("  ") }
            sb.append(s).append('\n')
        }
        fun walk(blocks: List<Block>, depth: Int) {
            for (b in blocks) when (b) {
                is TextFlowBlock -> {
                    line(depth, "flow#${b.flowId} (${b.paragraphs.size} paras)")
                    for (p in b.paragraphs) {
                        val styles = p.runs.joinToString(",") { r ->
                            val s = r.style
                            "${r.start}-${r.end}:${s.sizePt}pt" + (if (s.bold) " B" else "") + (if (s.italic) " I" else "")
                        }
                        line(depth + 1, "[${p.style.align} L${p.style.marginLeftPt} I${p.style.indentPt}] " +
                            "\"${p.text.replace("\t", "\\t").replace("\u2028", "\\n")}\" {$styles}")
                    }
                }
                is TableBlock -> {
                    line(depth, "table ${b.rowCount}x${b.colCount} widths=${b.columnWidths}")
                    for (c in b.cells) {
                        line(depth + 1, "cell r${c.row} c${c.col} span ${c.rowSpan}x${c.colSpan}")
                        walk(c.blocks, depth + 2)
                    }
                    if (b.caption.isNotEmpty()) {
                        line(depth + 1, "caption"); walk(b.caption, depth + 2)
                    }
                }
                is ImageBlock -> {
                    line(depth, "image ${b.width}x${b.height} bytes=${b.data?.size}")
                    walk(b.caption, depth + 1)
                }
                is BoxBlock -> {
                    line(depth, "box ${b.kind} ${b.label}")
                    walk(b.blocks, depth + 1)
                }
                is ObjectBlock -> line(depth, "object ${b.label} ${b.detail ?: ""}")
            }
        }
        line(0, "${model.format} bodyWidth=${model.bodyWidth} readOnly=${model.readOnlyReason}")
        walk(model.blocks, 0)
        return sb.toString()
    }
}
