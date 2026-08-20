package org.example.client

import kotlinx.serialization.json.Json
import org.example.client.data.network.dto.SessionDto
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

class SessionDtoTest {

    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun parsesBackendSessionPayload() {
        val payload = """
            {
              "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
              "title": "Morning reflection",
              "created_at": "2026-08-18T09:00:00Z",
              "ended_at": null,
              "is_active": true,
              "exchanges": [
                {
                  "id": "11111111-1111-1111-1111-111111111111",
                  "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                  "transcript": "I had a rough day",
                  "reflection": "That sounds hard",
                  "detected_mode": "venting",
                  "created_at": "2026-08-18T09:00:00Z"
                }
              ]
            }
        """.trimIndent()

        val dto = json.decodeFromString<SessionDto>(payload)

        assertEquals("3fa85f64-5717-4562-b3fc-2c963f66afa6", dto.id)
        assertEquals("Morning reflection", dto.title)
        assertEquals("2026-08-18T09:00:00Z", dto.createdAt)
        assertNull(dto.endedAt)
        assertEquals(true, dto.isActive)
        assertEquals(1, dto.exchanges.size)
        assertEquals("I had a rough day", dto.exchanges[0].transcript)
        assertEquals("venting", dto.exchanges[0].detectedMode)
    }
}