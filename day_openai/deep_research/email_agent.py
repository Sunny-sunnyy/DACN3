import os
from typing import Dict

import sendgrid
from sendgrid.helpers.mail import Email, Mail, Content, To
from agents import Agent, function_tool


# Tool gửi email qua dịch vụ SendGrid
@function_tool
def send_email(subject: str, html_body: str) -> Dict[str, str]:
    """Send an email with the given subject and HTML body"""
    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get("SENDGRID_API_KEY"))  # Kết nối SendGrid API
    from_email = Email("ed@edwarddonner.com")  # Email người gửi (cần verify trước)
    to_email = To("ed.donner@gmail.com")  # Email người nhận
    content = Content("text/html", html_body)  # Nội dung email dạng HTML
    mail = Mail(from_email, to_email, subject, content).get()  # Tạo đối tượng email
    response = sg.client.mail.send.post(request_body=mail)  # Gửi email
    print("Email response", response.status_code)
    return "success"


# Hướng dẫn cho agent: chuyển báo cáo thành email HTML đẹp và gửi đi
INSTRUCTIONS = """You are able to send a nicely formatted HTML email based on a detailed report.
You will be provided with a detailed report. You should use your tool to send one email, providing the 
report converted into clean, well presented HTML with an appropriate subject line."""

# Agent gửi email: nhận báo cáo -> chuyển thành HTML -> gửi email
email_agent = Agent(
    name="Email agent",
    instructions=INSTRUCTIONS,
    tools=[send_email],  # Sử dụng tool send_email
    model="gpt-4o-mini",
)
