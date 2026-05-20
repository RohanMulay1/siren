from ..registry import register_tool


@register_tool("DESTRUCTIVE")
class DrainLbNode:
    NAME = "drain_lb_node"
    DESCRIPTION = (
        "Remove a node from an AWS ALB target group, draining it from traffic. "
        "DESTRUCTIVE: reduces capacity. Requires human approval before execution."
    )
    INPUT_SCHEMA = {
        "type": "object",
        "properties": {
            "target_group_arn": {"type": "string", "description": "ARN of the ALB target group"},
            "instance_id": {"type": "string", "description": "EC2 instance ID to drain"},
            "port": {"type": "integer", "description": "Port the instance is registered on", "default": 80},
        },
        "required": ["target_group_arn", "instance_id"],
    }

    @staticmethod
    async def execute(target_group_arn: str, instance_id: str, port: int = 80) -> str:
        try:
            import boto3
            from siren.config import get_settings
            settings = get_settings()

            client = boto3.client("elbv2", region_name=settings.aws_default_region)
            client.deregister_targets(
                TargetGroupArn=target_group_arn,
                Targets=[{"Id": instance_id, "Port": port}],
            )
            return (
                f"Instance {instance_id} deregistered from target group "
                f"{target_group_arn}:{port}. Draining in progress."
            )
        except Exception as e:
            return f"[ALB drain error] {type(e).__name__}: {e}"
