output "vpc_id" {
  value = module.network.vpc_id
}

output "public_subnet_ids" {
  value = module.network.public_subnet_ids
}

output "private_subnet_ids" {
  value = module.network.private_subnet_ids
}

output "bastion_public_ip" {
  value = module.compute.bastion_public_ip
}

output "bastion_instance_id" {
  value = module.compute.bastion_instance_id
}

output "control_plane_instance_id" {
  value = module.compute.control_plane_instance_id
}

output "control_plane_private_ip" {
  value = module.compute.control_plane_private_ip
}

output "worker_instance_ids" {
  value = module.compute.worker_instance_ids
}

output "worker_private_ips" {
  value = module.compute.worker_private_ips
}

output "alb_dns_name" {
  value = module.alb.alb_dns_name
}

output "app_fqdn" {
  value = module.alb.fqdn
}

output "ecr_repository_urls" {
  value = module.ecr.repository_urls
}
