package org.example.client

import kotlinx.serialization.json.Json
import org.example.client.data.network.dto.MessageRole
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
              "user_id": "00000000-0000-0000-0000-000000000001",
              "title": "Morning journal",
              "created_at": "2026-08-18T09:00:00Z",
              "ended_at": null,
              "is_active": true,
              "messages": [
                {
                  "id": "11111111-1111-1111-1111-111111111111",
                  "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                  "role": "user",
                  "content": "I had a rough day",
                  "created_at": "2026-08-18T09:00:00Z"
                },
                {
                  "id": "22222222-2222-2222-2222-222222222222",
                  "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                  "role": "assistant",
                  "content": "That sounds hard",
                  "created_at": "2026-08-18T09:00:01Z"
                }
              ]
            }
        """.trimIndent()

        val dto = json.decodeFromString<SessionDto>(payload)

        assertEquals("3fa85f64-5717-4562-b3fc-2c963f66afa6", dto.id)
        assertEquals("Morning journal", dto.title)
        assertEquals("2026-08-18T09:00:00Z", dto.createdAt)
        assertNull(dto.endedAt)
        assertEquals(true, dto.isActive)
        assertEquals(2, dto.messages.size)
        assertEquals(MessageRole.User, dto.messages[0].role)
        assertEquals("I had a rough day", dto.messages[0].content)
        assertEquals(MessageRole.Assistant, dto.messages[1].role)
        assertEquals("That sounds hard", dto.messages[1].content)
    }
}
