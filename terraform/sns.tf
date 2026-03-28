# ── SNS Topic ──
resource "aws_sns_topic" "gpu_alerts" {
  name = "${var.app_name}-alerts"

  tags = {
    Name        = "${var.app_name}-alerts"
    Environment = var.environment
  }
}

# ── SMS Subscription ──
resource "aws_sns_topic_subscription" "sms" {
  topic_arn = aws_sns_topic.gpu_alerts.arn
  protocol  = "sms"
  endpoint  = var.alert_phone_number
}
