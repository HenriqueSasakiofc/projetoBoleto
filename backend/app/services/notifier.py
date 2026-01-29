class EmailNotifier:
    def enviar_email_boleto_gerado(self, para: str, cobranca_id: int, pdf_url: str, linha_digitavel: str):
        print("\n=== EMAIL (DEV) ===")
        print(f"Para: {para}")
        print(f"Assunto: Boleto gerado - Cobrança #{cobranca_id}")
        print(f"PDF: {pdf_url}")
        print(f"Linha digitável: {linha_digitavel}")
        print("===================\n")