package kr.naya.hwpedit

import android.content.ContentResolver
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.OpenableColumns
import java.io.IOException

/** 파일 읽기·쓰기와 최근 문서 목록. */
object Files {
    const val MAX_BYTES = 200L * 1024 * 1024

    fun displayName(cr: ContentResolver, uri: Uri): String {
        try {
            cr.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { c ->
                if (c.moveToFirst()) {
                    val i = c.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                    if (i >= 0) c.getString(i)?.let { if (it.isNotBlank()) return it }
                }
            }
        } catch (e: Exception) {
            // 이름을 못 얻어도 열기는 계속한다.
        }
        return uri.lastPathSegment?.substringAfterLast('/')?.takeIf { it.isNotBlank() } ?: "문서"
    }

    fun read(cr: ContentResolver, uri: Uri): ByteArray {
        val stream = cr.openInputStream(uri) ?: throw IOException("파일을 열 수 없어요.")
        stream.use { input ->
            val out = java.io.ByteArrayOutputStream()
            val buf = ByteArray(64 * 1024)
            var total = 0L
            while (true) {
                val n = input.read(buf)
                if (n < 0) break
                total += n
                if (total > MAX_BYTES) throw IOException("파일이 너무 커요(200MB 초과).")
                out.write(buf, 0, n)
            }
            return out.toByteArray()
        }
    }

    /**
     * 내용을 통째로 바꿔 쓴다. 다 쓴 뒤 다시 읽어서 똑같은지 확인한다.
     * 자르기(truncate)를 지원하지 않는 곳에는 쓰지 않는다(뒤에 옛 내용이 남아 파일이 깨질 수 있어서).
     */
    fun write(cr: ContentResolver, uri: Uri, bytes: ByteArray) {
        var lastError: Exception? = null
        var written = false
        for (mode in listOf("wt", "rwt")) {
            try {
                val out = cr.openOutputStream(uri, mode) ?: throw IOException("저장할 곳을 열 수 없어요.")
                out.use {
                    it.write(bytes)
                    it.flush()
                }
                written = true
                break
            } catch (e: SecurityException) {
                throw e
            } catch (e: Exception) {
                lastError = e
            }
        }
        if (!written) throw lastError ?: IOException("저장하지 못했어요.")
        val back = try {
            read(cr, uri)
        } catch (e: Exception) {
            null
        }
        if (back != null && !back.contentEquals(bytes)) {
            throw IOException("저장한 파일을 다시 읽어 보니 내용이 달라요. 다른 이름으로 저장해 주세요.")
        }
    }
}

class RecentDoc(val uri: Uri, val name: String, val time: Long)

/** 최근 문서. 다시 열 권한을 받은 문서만 기억한다. */
class Recents(context: Context) {
    private val prefs = context.getSharedPreferences("recents", Context.MODE_PRIVATE)

    fun list(): List<RecentDoc> {
        val raw = prefs.getString(KEY, "") ?: ""
        return raw.split('\n').mapNotNull { line ->
            val parts = line.split('\t')
            if (parts.size < 3) return@mapNotNull null
            val t = parts[2].toLongOrNull() ?: return@mapNotNull null
            RecentDoc(Uri.parse(parts[0]), parts[1], t)
        }
    }

    fun add(uri: Uri, name: String) {
        val items = list().filter { it.uri != uri }.toMutableList()
        items.add(0, RecentDoc(uri, name.replace('\t', ' ').replace('\n', ' '), System.currentTimeMillis()))
        save(items.take(MAX))
    }

    fun remove(uri: Uri) = save(list().filter { it.uri != uri })

    private fun save(items: List<RecentDoc>) {
        prefs.edit().putString(KEY, items.joinToString("\n") { "${it.uri}\t${it.name}\t${it.time}" }).apply()
    }

    companion object {
        private const val KEY = "items"
        private const val MAX = 20

        /** 파일 선택기로 고른 문서는 앱을 다시 켜도 열 수 있도록 권한을 붙잡아 둔다. */
        fun keepPermission(context: Context, uri: Uri, flags: Int): Boolean = try {
            val f = flags and (Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
            context.contentResolver.takePersistableUriPermission(uri, f)
            true
        } catch (e: Exception) {
            false
        }

        fun hasPermission(context: Context, uri: Uri): Boolean =
            context.contentResolver.persistedUriPermissions.any { it.uri == uri && it.isReadPermission }
    }
}

object Prefs {
    private const val NAME = "settings"

    /** 1포인트를 몇 sp 로 그릴지. */
    fun textScale(context: Context): Float =
        context.getSharedPreferences(NAME, Context.MODE_PRIVATE).getFloat("textScale", 1.5f)

    fun setTextScale(context: Context, v: Float) {
        context.getSharedPreferences(NAME, Context.MODE_PRIVATE).edit().putFloat("textScale", v).apply()
    }
}
