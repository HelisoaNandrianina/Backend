def send_reset_email(to_email: str, reset_token: str) -> None:
    reset_link = f"http://localhost:5173/reset-password?token={reset_token}"
    print(f"[DEV] Email de réinitialisation pour {to_email} : {reset_link}")