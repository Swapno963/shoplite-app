resource "aws_security_group" "bastion" {
  name        = "${var.project_name}-bastion-sg"
  description = "SSH from admin CIDR; SSM egress"
  vpc_id      = var.vpc_id

  ingress {
    description = "SSH from administrators"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.admin_cidr]
  }

  egress {
    description = "SSH to private nodes"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description = "HTTPS for SSM and packages"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "HTTP for package mirrors"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-bastion-sg"
  }
}

resource "aws_security_group" "control_plane" {
  name        = "${var.project_name}-cp-sg"
  description = "Kubernetes control plane; not reachable from the internet"
  vpc_id      = var.vpc_id

  tags = {
    Name = "${var.project_name}-cp-sg"
  }
}

resource "aws_security_group" "worker" {
  name        = "${var.project_name}-worker-sg"
  description = "Kubernetes workers; not reachable from the internet"
  vpc_id      = var.vpc_id

  tags = {
    Name = "${var.project_name}-worker-sg"
  }
}

resource "aws_security_group_rule" "cp_ssh_from_bastion" {
  type                     = "ingress"
  description              = "SSH from bastion"
  from_port                = 22
  to_port                  = 22
  protocol                 = "tcp"
  security_group_id        = aws_security_group.control_plane.id
  source_security_group_id = aws_security_group.bastion.id
}

resource "aws_security_group_rule" "worker_ssh_from_bastion" {
  type                     = "ingress"
  description              = "SSH from bastion"
  from_port                = 22
  to_port                  = 22
  protocol                 = "tcp"
  security_group_id        = aws_security_group.worker.id
  source_security_group_id = aws_security_group.bastion.id
}

resource "aws_security_group_rule" "cp_api_from_workers" {
  type                     = "ingress"
  description              = "kube-apiserver from workers"
  from_port                = 6443
  to_port                  = 6443
  protocol                 = "tcp"
  security_group_id        = aws_security_group.control_plane.id
  source_security_group_id = aws_security_group.worker.id
}

resource "aws_security_group_rule" "cp_api_from_self" {
  type              = "ingress"
  description       = "kube-apiserver from control plane"
  from_port         = 6443
  to_port           = 6443
  protocol          = "tcp"
  security_group_id = aws_security_group.control_plane.id
  self              = true
}

resource "aws_security_group_rule" "cp_etcd" {
  type              = "ingress"
  description       = "etcd"
  from_port         = 2379
  to_port           = 2380
  protocol          = "tcp"
  security_group_id = aws_security_group.control_plane.id
  self              = true
}

resource "aws_security_group_rule" "cp_kubelet_from_workers" {
  type                     = "ingress"
  description              = "kubelet from workers"
  from_port                = 10250
  to_port                  = 10250
  protocol                 = "tcp"
  security_group_id        = aws_security_group.control_plane.id
  source_security_group_id = aws_security_group.worker.id
}

resource "aws_security_group_rule" "worker_kubelet_from_cp" {
  type                     = "ingress"
  description              = "kubelet from control plane"
  from_port                = 10250
  to_port                  = 10250
  protocol                 = "tcp"
  security_group_id        = aws_security_group.worker.id
  source_security_group_id = aws_security_group.control_plane.id
}

resource "aws_security_group_rule" "worker_kubelet_from_self" {
  type              = "ingress"
  description       = "kubelet between workers"
  from_port         = 10250
  to_port           = 10250
  protocol          = "tcp"
  security_group_id = aws_security_group.worker.id
  self              = true
}

resource "aws_security_group_rule" "cp_vxlan" {
  type              = "ingress"
  description       = "Flannel/Calico VXLAN from VPC"
  from_port         = 8472
  to_port           = 8472
  protocol          = "udp"
  security_group_id = aws_security_group.control_plane.id
  cidr_blocks       = [var.vpc_cidr]
}

resource "aws_security_group_rule" "worker_vxlan" {
  type              = "ingress"
  description       = "Flannel/Calico VXLAN from VPC"
  from_port         = 8472
  to_port           = 8472
  protocol          = "udp"
  security_group_id = aws_security_group.worker.id
  cidr_blocks       = [var.vpc_cidr]
}

resource "aws_security_group_rule" "worker_nodeports" {
  type              = "ingress"
  description       = "NodePorts from VPC"
  from_port         = 30000
  to_port           = 32767
  protocol          = "tcp"
  security_group_id = aws_security_group.worker.id
  cidr_blocks       = [var.vpc_cidr]
}

resource "aws_security_group_rule" "worker_ingress_from_alb" {
  type                     = "ingress"
  description              = "Ingress from ALB"
  from_port                = var.ingress_node_port
  to_port                  = var.ingress_node_port
  protocol                 = "tcp"
  security_group_id        = aws_security_group.worker.id
  source_security_group_id = var.alb_security_group_id
}

resource "aws_security_group_rule" "cp_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  security_group_id = aws_security_group.control_plane.id
  cidr_blocks       = ["0.0.0.0/0"]
}

resource "aws_security_group_rule" "worker_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  security_group_id = aws_security_group.worker.id
  cidr_blocks       = ["0.0.0.0/0"]
}
