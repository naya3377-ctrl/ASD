package kr.naya.hwpedit.core

import kr.dogfoot.hwplib.reader.HWPReader
import kr.dogfoot.hwplib.writer.HWPWriter
import kr.dogfoot.hwpxlib.reader.HWPXReader
import kr.dogfoot.hwpxlib.writer.HWPXWriter
import kr.naya.hwpedit.core.hwp.HwpAdapter
import kr.naya.hwpedit.core.hwpx.HwpxAdapter
import kr.naya.hwpedit.core.hwpx.HwpxPackage
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.File

/** 사용자에게 그대로 보여 줄 수 있는 한국어 메시지를 담은 오류. */
class DocumentException(message: String, cause: Throwable? = null) : Exception(message, cause)

class OpenedDocument(val format: DocFormat, val model: DocModel)

/**
 * 앱이 쓰는 입구.
 *
 * 열기: open(파일 내용) -> 화면용 모델
 * 저장: save(원래 파일 내용, 고친 흐름들) -> 새 파일 내용
 *
 * 저장할 때는 원래 파일을 새로 읽어 고친 부분만 반영하고, 만든 결과를 다시 읽어서
 * 글이 의도대로 들어갔는지 확인한 뒤에만 돌려준다. 확인에 실패하면 예외를 던지고
 * 원래 파일은 건드리지 않는다.
 */
object HwpDocuments {

    fun detect(bytes: ByteArray): DocFormat? {
        if (bytes.size >= 8 &&
            bytes[0] == 0xD0.toByte() && bytes[1] == 0xCF.toByte() &&
            bytes[2] == 0x11.toByte() && bytes[3] == 0xE0.toByte()
        ) return DocFormat.HWP
        if (bytes.size >= 4 && bytes[0] == 'P'.code.toByte() && bytes[1] == 'K'.code.toByte()) return DocFormat.HWPX
        return null
    }

    fun open(bytes: ByteArray): OpenedDocument {
        val format = detectOrThrow(bytes)
        val adapter = load(bytes, format)
        return OpenedDocument(format, buildModel(adapter))
    }

    /**
     * @param opened 같은 원본으로 open() 해 둔 모델이 있으면 넘긴다(다시 읽는 시간을 아낀다).
     */
    fun save(original: ByteArray, edits: Map<Int, String>, opened: DocModel? = null): ByteArray {
        val format = detectOrThrow(original)
        val before = opened ?: buildModel(load(original, format))
        before.readOnlyReason?.let { throw DocumentException(it) }

        val adapter = load(original, format)
        buildModel(adapter) // 흐름 번호를 처음 열 때와 똑같이 매긴다.
        try {
            adapter.applyEdits(edits)
        } catch (e: DocumentException) {
            throw e
        } catch (e: Exception) {
            throw DocumentException("고친 내용을 문서에 반영하지 못했어요.", e)
        }

        var out = try {
            write(adapter, format)
        } catch (e: Exception) {
            throw DocumentException("문서를 저장 형식으로 만들지 못했어요.", e)
        }
        if (format == DocFormat.HWPX) out = HwpxPackage.normalize(out, original, null)

        val after = verify(before, edits, out, format)
        if (format == DocFormat.HWPX && edits.isNotEmpty()) {
            out = HwpxPackage.normalize(out, original, HwpxPackage.previewText(after))
            verify(before, edits, out, format)
        }
        return out
    }

    /** 저장 결과를 다시 읽어, 글과 개체 수가 기대한 대로인지 확인한다. */
    private fun verify(before: DocModel, edits: Map<Int, String>, out: ByteArray, format: DocFormat): DocModel {
        val after = try {
            buildModel(load(out, format))
        } catch (e: Exception) {
            throw DocumentException("저장한 결과를 다시 열어 보니 읽을 수 없었어요. 원래 파일은 그대로 두었어요.", e)
        }

        val expected = ArrayList<String>()
        for (flow in before.allFlows()) {
            val text = edits[flow.flowId]?.let { SpecialChars.sanitize(it) } ?: flow.text
            text.split('\n').filterTo(expected) { it.isNotEmpty() }
        }
        val actual = after.allFlows().flatMap { f -> f.text.split('\n').filter { it.isNotEmpty() } }
        if (expected != actual) {
            val i = expected.indices.firstOrNull { it >= actual.size || expected[it] != actual[it] } ?: actual.size
            throw DocumentException(
                "저장 결과를 확인해 보니 글이 의도와 달라요(${i + 1}번째 문단 부근). 원래 파일은 그대로 두었어요.",
            )
        }
        val c1 = countObjects(before)
        val c2 = countObjects(after)
        if (c1 != c2) {
            throw DocumentException("저장 결과를 확인해 보니 표나 그림 수가 달라졌어요. 원래 파일은 그대로 두었어요.")
        }
        return after
    }

    private fun countObjects(model: DocModel): Map<String, Int> {
        val counts = HashMap<String, Int>()
        fun walk(blocks: List<Block>) {
            for (b in blocks) when (b) {
                is TableBlock -> {
                    counts.merge("table", 1, Int::plus)
                    b.cells.forEach { walk(it.blocks) }
                    walk(b.caption)
                }
                is ImageBlock -> {
                    counts.merge("image", 1, Int::plus); walk(b.caption)
                }
                is BoxBlock -> {
                    counts.merge(b.kind.name, 1, Int::plus); walk(b.blocks)
                }
                is ObjectBlock -> counts.merge("object", 1, Int::plus)
                is TextFlowBlock -> {}
            }
        }
        walk(model.blocks)
        return counts
    }

    /** 문서 안의 보이지 않는 개체(표, 필드 표시, 구역 정의 등) 수. 저장 전후 비교용. */
    internal fun anchorCount(bytes: ByteArray): Int {
        val adapter = load(bytes, detectOrThrow(bytes))
        buildModel(adapter)
        return adapter.anchorsSeen
    }

    private fun detectOrThrow(bytes: ByteArray): DocFormat {
        detect(bytes)?.let { return it }
        val head = String(bytes, 0, minOf(bytes.size, 32), Charsets.ISO_8859_1)
        if (head.startsWith("HWP Document File")) {
            throw DocumentException("한글 97 이전(3.0) 형식이라 열 수 없어요. 한글에서 새 형식(.hwp/.hwpx)으로 저장해 주세요.")
        }
        throw DocumentException("한글 문서(.hwp/.hwpx)가 아니거나 파일이 손상되었어요.")
    }

    private fun load(bytes: ByteArray, format: DocFormat): DocumentAdapter<*, *> = when (format) {
        DocFormat.HWP -> {
            val file = try {
                HWPReader.fromInputStream(ByteArrayInputStream(bytes))
            } catch (e: Exception) {
                if (e.message?.contains("password", ignoreCase = true) == true) {
                    throw DocumentException("암호가 걸린 문서는 아직 열 수 없어요.", e)
                }
                throw DocumentException("hwp 파일을 읽지 못했어요. 파일이 손상되었을 수 있어요.", e)
            } ?: throw DocumentException("hwp 파일을 읽지 못했어요.")
            HwpAdapter(file)
        }
        DocFormat.HWPX -> {
            // hwpx 는 zip 이라 임시 파일로 읽는다. 안드로이드 기본 XML 해석기에 맞춰 이름공간 처리는 끈다.
            val tmp = File.createTempFile("hwpx-", ".hwpx")
            try {
                tmp.writeBytes(bytes)
                val file = try {
                    HWPXReader.fromFile(tmp, false)
                } catch (e: Exception) {
                    throw DocumentException("hwpx 파일을 읽지 못했어요. 암호가 걸렸거나 파일이 손상되었을 수 있어요.", e)
                } ?: throw DocumentException("hwpx 파일을 읽지 못했어요.")
                HwpxAdapter(file)
            } finally {
                tmp.delete()
            }
        }
    }

    private fun buildModel(adapter: DocumentAdapter<*, *>): DocModel = try {
        when (adapter) {
            is HwpAdapter -> adapter.buildModel()
            is HwpxAdapter -> adapter.buildModel()
            else -> error("unknown adapter")
        }
    } catch (e: DocumentException) {
        throw e
    } catch (e: Exception) {
        throw DocumentException("문서 내용을 해석하지 못했어요.", e)
    }

    private fun write(adapter: DocumentAdapter<*, *>, format: DocFormat): ByteArray {
        val bos = ByteArrayOutputStream()
        when (adapter) {
            is HwpAdapter -> HWPWriter.toStream(adapter.file, bos)
            is HwpxAdapter -> HWPXWriter.toStream(adapter.file, bos)
            else -> error("unknown adapter for $format")
        }
        return bos.toByteArray()
    }
}
