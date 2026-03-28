# ── Application Load Balancer ──
# ALB operates at Layer 7 (HTTP/HTTPS). Unlike a direct ECS public IP
# which changes every task restart, the ALB DNS name is stable forever —
# this is what your Cloudflare CNAME will point at.
resource "aws_lb" "app" {
  name               = "${var.app_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  tags = {
    Name        = "${var.app_name}-alb"
    Environment = var.environment
  }
}

# ── Target Group ──
# The ALB forwards incoming requests here. target_type = "ip" is required
# for Fargate — there's no EC2 instance to register, so ECS registers
# each task's private IP directly when it starts up.
resource "aws_lb_target_group" "app" {
  name        = "${var.app_name}-tg"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
    timeout             = 5
    matcher             = "200"
  }

  tags = {
    Name        = "${var.app_name}-tg"
    Environment = var.environment
  }
}

# ── HTTP Listener ──
# Listens on port 80 and forwards all traffic to the target group.
# Port 80 is all we need since Cloudflare handles SSL termination
# on its end when proxy mode (orange cloud) is enabled.
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.app.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}
