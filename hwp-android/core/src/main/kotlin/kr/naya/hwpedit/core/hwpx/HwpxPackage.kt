package kr.naya.hwpedit.core.hwpx

import kr.naya.hwpedit.core.Block
import kr.naya.hwpedit.core.BoxBlock
import kr.naya.hwpedit.core.DocModel
import kr.naya.hwpedit.core.ImageBlock
import kr.naya.hwpedit.core.ObjectBlock
import kr.naya.hwpedit.core.SpecialChars
import kr.naya.hwpedit.core.TableBlock
import kr.naya.hwpedit.core.TextFlowBlock
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.util.zip.CRC32
import java.util.zip.ZipEntry
import java.util.zip.ZipInputStream
import java.util.zip.ZipOutputStream

/**
 * hwpx 압축 파일을 한컴 오피스가 만드는 모양으로 다듬는다.
 *  - mimetype 을 맨 앞에, 압축하지 않고 둔다(OCF 규칙).
 *  - 라이브러리가 읽지 못해 빠뜨린 파일(메모 확장 정보, 스크립트 등)을 원본에서 되살린다.
 *    목록(content.hpf)에는 남아 있는데 파일이 없으면 문서가 깨지기 때문이다.
 *  - 미리보기 글(Preview/PrvText.txt)을 고친 내용으로 바꾼다. 미리보기 그림은 옛 내용이므로 되살리지 않는다.
 */
internal object HwpxPackage {
    private const val MIMETYPE = "mimetype"
    private const val PREVIEW_TEXT = "Preview/PrvText.txt"
    private const val PREVIEW_IMAGE = "Preview/PrvImage.png"
    private const val PREVIEW_LIMIT = 1024

    private fun readEntries(bytes: ByteArray): LinkedHashMap<String, ByteArray> {
        val entries = LinkedHashMap<String, ByteArray>()
        ZipInputStream(ByteArrayInputStream(bytes)).use { zin ->
            while (true) {
                val e = zin.nextEntry ?: break
                if (!e.isDirectory) entries[e.name] = zin.readBytes()
            }
        }
        return entries
    }

    fun normalize(bytes: ByteArray, original: ByteArray, previewText: String?): ByteArray {
        val entries = readEntries(bytes)
        val mimetype = entries.remove(MIMETYPE) ?: return bytes
        for ((name, data) in readEntries(original)) {
            if (name == MIMETYPE || name == PREVIEW_IMAGE || entries.containsKey(name)) continue
            entries[name] = data
        }
        if (previewText != null && entries.containsKey(PREVIEW_TEXT)) {
            entries[PREVIEW_TEXT] = previewText.toByteArray(Charsets.UTF_8)
        }

        val bos = ByteArrayOutputStream(bytes.size + 1024)
        ZipOutputStream(bos).use { zout ->
            val crc = CRC32().apply { update(mimetype) }
            val me = ZipEntry(MIMETYPE).apply {
                method = ZipEntry.STORED
                size = mimetype.size.toLong()
                compressedSize = mimetype.size.toLong()
                this.crc = crc.value
            }
            zout.putNextEntry(me)
            zout.write(mimetype)
            zout.closeEntry()
            for ((name, data) in entries) {
                zout.putNextEntry(ZipEntry(name).apply { method = ZipEntry.DEFLATED })
                zout.write(data)
                zout.closeEntry()
            }
        }
        return bos.toByteArray()
    }

    /** 한컴 오피스의 미리보기 글과 비슷하게: 문단은 줄바꿈, 표 칸은 <...> 로 감싼다. */
    fun previewText(model: DocModel): String {
        val sb = StringBuilder()
        fun clean(s: String) = s.replace(SpecialChars.LINE_BREAK, ' ').replace('\t', ' ')
        fun walk(blocks: List<Block>, inCell: Boolean) {
            for (b in blocks) {
                if (sb.length >= PREVIEW_LIMIT) return
                when (b) {
                    is TextFlowBlock -> if (inCell) {
                        sb.append(clean(b.text).replace('\n', ' '))
                    } else {
                        for (p in b.paragraphs) sb.append(clean(p.text)).append("\r\n")
                    }
                    is TableBlock -> {
                        var row = -1
                        for (c in b.cells.sortedWith(compareBy({ it.row }, { it.col }))) {
                            if (c.row != row) {
                                if (row >= 0) sb.append("\r\n")
                                row = c.row
                            }
                            sb.append('<')
                            walk(c.blocks, true)
                            sb.append('>')
                        }
                        sb.append("\r\n")
                    }
                    is BoxBlock -> walk(b.blocks, inCell)
                    is ImageBlock, is ObjectBlock -> {}
                }
            }
        }
        walk(model.blocks, false)
        return if (sb.length > PREVIEW_LIMIT) sb.substring(0, PREVIEW_LIMIT) else sb.toString()
    }
}
