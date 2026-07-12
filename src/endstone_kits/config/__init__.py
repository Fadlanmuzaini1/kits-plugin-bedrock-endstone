"""
Lapisan konfigurasi.

Tanggung jawab: menyediakan akses bertipe (typed) ke `self.config`
bawaan Endstone (dibaca dari config.toml), sehingga seluruh codebase
tidak mengakses dict config secara mentah (`config["storage"]["..."]`)
tersebar di banyak tempat.
"""
