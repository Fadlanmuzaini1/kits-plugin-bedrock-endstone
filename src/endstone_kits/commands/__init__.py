"""
Parsing argumen command & pengiriman feedback pesan ke player/console.

Aturan: folder ini TIDAK boleh berisi business logic (validasi kit,
perhitungan cooldown, dll) -- itu tanggung jawab `managers/`. Command
handler di sini hanya: parse args -> panggil 1 method manager -> ubah
hasilnya jadi pesan ke sender.
"""
