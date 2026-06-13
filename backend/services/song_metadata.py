import httpx

from config import settings


async def search_song_metadata(song_name: str, artist_name: str, client: httpx.AsyncClient) -> dict:
    response = await client.get(
        "/",
        params={
            "method": "track.getInfo",
            "api_key": settings.lastfm_api_key,
            "artist": artist_name,
            "track": song_name,
            "format": "json",
        },
    )
    response.raise_for_status()
    data = response.json()
    track = data.get("track", {})
    return {
        "title": track.get("name"),
        "artist": track.get("artist", {}).get("name"),
        "album": track.get("album", {}).get("title") if track.get("album") else None,
        "mbid": track.get("mbid"),
        "tags": track.get("toptags", {}).get("tag", []),
    }
