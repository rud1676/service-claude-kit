# draw.io AWS4 아이콘 이름표

draw.io v32.4.1 번들(app.asar)에서 추출. **여기 없는 이름을 쓰면 빈 사각형으로 렌더된다** — 렌더 후 PNG에서 아이콘이 비어 있으면 이름부터 의심할 것.
(실제 사례: `elastic_container_registry` ✗ → `ecr` ✓, `opensearch_service`·`bedrock`·`efs` ✗)

## 자주 쓰는 것 → `icon(res, color)`
| 서비스 | res | 색 |
|---|---|---|
| CloudFront / Route 53 / ELB / ALB / API GW | cloudfront / route_53 / elastic_load_balancing / application_load_balancer / api_gateway | C.NET |
| EC2 / ECS / EKS / Fargate / Lambda / ECR / Lightsail | ec2 / ecs / eks / fargate / lambda / ecr / lightsail | C.COMPUTE |
| S3 / EBS / Backup | s3 / elastic_block_store / backup | C.STORAGE |
| RDS / Aurora / DynamoDB / ElastiCache | rds / aurora / dynamodb / elasticache | C.DB |
| IAM / WAF / ACM / Secrets Manager / KMS / Cognito / Shield | identity_and_access_management / waf / certificate_manager_3 / secrets_manager / key_management_service / cognito / shield | C.SECURITY |
| CloudWatch / SSM(Parameter Store 포함) / SNS / SQS / EventBridge / CloudTrail / Step Functions | cloudwatch_2 / systems_manager / sns / sqs / eventbridge / cloudtrail / step_functions | C.MGMT |
| SES | simple_email_service | C.SECURITY |
| CodePipeline / CodeBuild | codepipeline / codebuild | "#C925D1" |

## 단독 shape → `f"...shape=mxgraph.aws4.{name};"` (resIcon 아님)
users, user, client, mobile_client, internet, internet_gateway, nat_gateway, vpn_gateway, customer_gateway, endpoint, bucket, t3_instance, instances, container_1 …
사람은 `person("users")` / `person("user")`.

## 그룹 → `grp(icon, stroke, ...)`
| 용도 | grIcon | stroke |
|---|---|---|
| AWS Cloud | group_aws_cloud_alt | #232F3E |
| Region | group_region (dashed=1) | #00A4A6 |
| VPC | group_vpc2 (또는 group_vpc) | #8C4FFF |
| Subnet(퍼블릭) | group_security_group, fill=#F2F6E8 | #7AA116 |
| Subnet(프라이빗) | group_security_group, fill=#E6F2F8 | #147EBA |
| EC2 인스턴스 내부 | group_ec2_instance_contents | #D86613 |
| Auto Scaling | group_auto_scaling_group | #D86613 |
| 온프레미스/외부 DC | group_corporate_data_center / group_on_premise | #7D8998 |

## 전체 resIcon 목록
 alexa_for_business alexa_smart_home_skill amplify analytics apache_mxnet_on_aws api_gateway app_mesh application_discovery_service application_integration application_load_balancer appstream_20 appsync ar_vr artifact athena aurora auto_scaling2 autoscaling backup batch blockchain bottlerocket braket budgets business_application certificate_manager_3 chime classic_load_balancer client_vpn cloud9 cloud_development_kit cloud_directory cloud_map cloudendure_migration cloudformation cloudfront cloudhsm cloudsearch cloudsearch2 cloudtrail cloudwatch cloudwatch_2 codebuild codecommit codedeploy codeguru_2 codepipeline codestar cognito command_line_interface comprehend compute config connect control_tower cost_and_usage_report cost_explorer cost_management customer_enablement customer_engagement data_pipeline database database_migration_service datasync db_instance db_instance_read_replica db_instance_standby db_on_instance deep_learning_amis deep_learning_containers deeplens deepracer desktop_and_app_streaming developer_tools device_farm direct_connect directory_service documentdb_with_mongodb_compatibility dynamodb ec2 ecr ecs efs_infrequentaccess efs_standard eks elastic_beanstalk elastic_block_store elastic_file_system elastic_inference elastic_inference_2 elastic_load_balancing elastic_transcoder elasticache elasticsearch_service elemental elemental_mediaconnect elemental_mediaconvert elemental_medialive elemental_mediapackage elemental_mediastore elemental_mediatailor emr eventbridge fargate firewall_manager forecast freertos fsx fsx_for_lustre fsx_for_windows_file_server game_tech game_tech2 gamelift general glacier global_accelerator glue greengrass ground_station guardduty identity_and_access_management inspector internet_of_things iot_1click iot_analytics iot_button iot_core iot_device_defender iot_device_management iot_events iot_sitewise iot_things_graph iq key_management_service kinesis kinesis_data_analytics kinesis_data_firehose kinesis_data_streams kinesis_video_streams lake_formation lambda lex license_manager lightsail machine_learning macie managed_blockchain managed_services managed_streaming_for_kafka management_and_governance management_console marketplace media_services migration_and_transfer migration_hub mobile mobile_hub mq ms_sql_instance ms_sql_instance_alternate mysql_db_instance mysql_db_instance_alternate neptune networking_and_content_delivery opsworks oracle_db_instance oracle_db_instance_alternate organizations outposts personal_health_dashboard personalize pinpoint piop polly postgresql_instance professional_services quantum_ledger_database quantum_technologies quicksight rds rds_on_vmware redshift rekognition rekognition_image rekognition_video reserved_instance_reporting resource_access_manager robomaker robotics route_53 s3 sagemaker sagemaker_ground_truth sagemaker_model sagemaker_notebook sagemaker_train satellite savings_plans secrets_manager security_hub security_identity_and_compliance server_migration_service serverless_application_repository service_catalog shield simple_email_service single_sign_on site_to_site_vpn snowball snowball_edge snowmobile sns sql_primary sql_replica sqs step_functions storage storage_gateway sumerian support systems_manager tensorflow_on_aws textract thinkbox_deadline thinkbox_draft thinkbox_frost thinkbox_krakatoa thinkbox_sequoia thinkbox_stoke thinkbox_xmesh timestream tools_and_sdks transcribe transfer_family transfer_for_sftp transit_gateway translate trusted_advisor vmware_cloud_on_aws vpc vpc_privatelink waf well_architected_tool workdocs worklink workmail workspaces xray 
