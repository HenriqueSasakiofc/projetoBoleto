import uuid

class MockBoletoProvider:
    def gerar_boleto(self, *, valor: float, vencimento, sacado_nome: str):
        charge_id = str(uuid.uuid4())
        linha = "34191.79001 01043.510047 91020.150008 8 12340000010000"
        pdf_url = f"https://exemplo.local/boleto/{charge_id}.pdf"

        return {
            "provider_charge_id": charge_id,
            "linha_digitavel": linha,
            "pdf_url": pdf_url,
        }