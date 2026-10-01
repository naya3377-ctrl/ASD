package kr.naya.hwpedit.core

import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.File

/**
 * -Dhwp.bulkDir=폴더 를 주면 그 폴더 아래 모든 hwp/hwpx 를 열고, 모든 글 흐름 끝에 글을 덧붙여 저장해 본다.
 * (저장소에 넣기 어려운 실제 문서로 시험할 때 쓴다.)
 */
class BulkFilesTest {
    @Test
    fun openEditSaveEveryFile() {
        val dir = System.getProperty("hwp.bulkDir")
        assumeTrue(dir != null && File(dir).isDirectory)
        val files = File(dir!!).walk().filter { it.isFile && (it.extension == "hwp" || it.extension == "hwpx") }.toList()
        val report = StringBuilder()
        var ok = 0
        var readOnly = 0
        val failed = ArrayList<String>()
        for (f in files.sortedBy { it.path }) {
            val bytes = f.readBytes()
            val t0 = System.currentTimeMillis()
            try {
                val model = HwpDocuments.open(bytes).model
                val t1 = System.currentTimeMillis()
                if (model.readOnlyReason != null) {
                    readOnly++
                    report.append("RO   ${f.name}: ${model.readOnlyReason}\n")
                    continue
                }
                val flows = model.allFlows()
                val edits = flows.associate { it.flowId to it.text + " [수정]" }
                val saved = HwpDocuments.save(bytes, edits)
                val t2 = System.currentTimeMillis()
                val anchorsBefore = HwpDocuments.anchorCount(bytes)
                val anchorsAfter = HwpDocuments.anchorCount(saved)
                check(anchorsBefore == anchorsAfter) { "개체 수 $anchorsBefore -> $anchorsAfter" }
                ok++
                report.append("OK   ${f.name} (${bytes.size / 1024}KB, flows=${flows.size}, open=${t1 - t0}ms, save=${t2 - t1}ms)\n")
            } catch (e: Throwable) {
                var c: Throwable? = e
                val chain = StringBuilder()
                while (c != null) {
                    chain.append(" <- ").append(c.javaClass.simpleName).append(": ").append(c.message?.take(160))
                    c = c.cause
                }
                failed.add(f.name)
                report.append("FAIL ${f.name}:$chain\n")
            }
        }
        report.append("\n총 ${files.size}개: 성공 $ok, 읽기 전용 $readOnly, 실패 ${failed.size}\n")
        TestSupport.output("bulk-report.txt", report.toString().toByteArray())
        println(report)
    }
}
