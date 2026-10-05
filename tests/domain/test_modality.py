import json
import unittest

from buscador_empleos.domain.modality import Modality, detect_modality


class DetectModalityTest(unittest.TestCase):
    def test_header_wins_over_description(self):
        self.assertEqual(detect_modality("Analista Semipresencial", "ofrecemos trabajo remoto"), "Híbrido")
        self.assertEqual(detect_modality("Dev Remoto", "ir a la oficina 3 días"), "Remoto")

    def test_hybrid_beats_remote(self):
        self.assertEqual(detect_modality("Dev híbrido remoto"), "Híbrido")

    def test_explicit_modality_line_in_the_description(self):
        text = "Condiciones. Modalidad de trabajo: Tiempo completo / Presencial. Horario 8-5"
        self.assertEqual(detect_modality("Dev", text), "Presencial")

    def test_free_text_then_unknown(self):
        self.assertEqual(detect_modality("Dev", "Puedes trabajar desde casa"), "Remoto")
        self.assertEqual(detect_modality("Dev", "Sin información"), "No indicado")

    def test_remote_synonyms(self):
        for word in ("teletrabajo", "home office", "desde casa", "100% virtual", "remoto"):
            self.assertEqual(detect_modality(f"Dev {word}"), "Remoto", word)


class ModalityEnumTest(unittest.TestCase):
    def test_values_are_the_stored_strings(self):
        self.assertEqual([m.value for m in Modality], ["Remoto", "Híbrido", "Presencial", "No indicado"])

    def test_serializes_to_json_as_a_plain_string(self):
        self.assertEqual(json.dumps(Modality.REMOTE), '"Remoto"')
        self.assertEqual(Modality.REMOTE, "Remoto")


if __name__ == "__main__":
    unittest.main()
