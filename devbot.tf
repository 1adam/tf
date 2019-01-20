provider "aws" {
  region  = "us-east-1"
}

resource "aws_sqs_queue" "devbot-queue" {
  name_prefix  = "devbot-proc-queue"
  delay_seconds = 0
  max_message_size = 262144
  message_retention_seconds = 600
  visibility_timeout_seconds = 60
}

resource "aws_iam_role" "devbot_lambda_role" {
  name  = "devbot-lambda-role"
  depends_on  = ["aws_sqs_queue.devbot-queue"]
  assume_role_policy = <<EoP
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": "tfLambdaAssume001"
    }
  ]
}
EoP
}

resource "aws_lambda_function" "proc_new_msg" {
  filename      = "lambda__proc-new-msg.zip"
  function_name = "devbot_proc-new-msg"
  role          = "${aws_iam_role.devbot_lambda_role.arn}"
  handler       = "exports.proc_new_msg"
  source_code_hash  = "${base64sha256(file("lambda__proc-new-msg.zip"))}"
  runtime       = "python2.7"
  timeout       = 30
  depends_on    = ["aws_iam_role.devbot_lambda_role"]
}

resource "aws_cloudwatch_log_group" "devbot_lambda_log" {
  name  = "/aws/lambda/${aws_lambda_function.proc_new_msg.function_name}"
  retention_in_days = 14
}

resource "aws_iam_policy" "devbot_lambda_logging_policy" {
  name  = "devbot-lambda-log-pol"
  path  = "/"
  description = "IAM policy allowing logging from lambda"
  policy = <<EoP
{
  "Version": "2012-10-17",
  "Statement": {
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": [
        "arn:aws:logs:*:*:${aws_cloudwatch_log_group.devbot_lambda_log.name}",
        "arn:aws:logs:*:*:${aws_cloudwatch_log_group.devbot_lambda_log.name}:*"
      ],
      "Effect": "Allow"
  }
}
EoP
}

resource "aws_iam_policy" "devbot_lambda_ec2_policy" {
  name  = "devbot-lambda-ec2-pol"
  path  = "/"
  description = "IAM policy allowing ec2:RunInstances from lambda"
  policy = <<EoP
{
  "Version": "2012-10-17",
  "Statement": {
      "Action": [
        "ec2:*"
      ],
      "Resource": [
        "*"
      ],
      "Effect": "Allow"
  }
}
EoP
}

resource "aws_iam_policy" "devbot_lambda_sqs_policy" {
  name  = "devbot-lambda-sqs-pol"
  path  = "/"
  description = "IAM policy allowing sqs: from lambda"
  policy = <<EoP
{
  "Version": "2012-10-17",
  "Statement": {
      "Action": [
        "sqs:ReceiveMessage",
        "sqs:SendMessage",
        "sqs:SendMessageBatch",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes"
      ],
      "Resource": [
        "${aws_sqs_queue.devbot-queue.arn}",
        "${aws_sqs_queue.devbot-queue.arn}/*"
      ],
      "Effect": "Allow"
  }
}
EoP
}

resource "aws_iam_role_policy_attachment" "devbot_lambda_logs" {
  role  = "${aws_iam_role.devbot_lambda_role.name}"
  policy_arn  = "${aws_iam_policy.devbot_lambda_logging_policy.arn}"
}

resource "aws_iam_role_policy_attachment" "devbot_lambda_ec2" {
  role  = "${aws_iam_role.devbot_lambda_role.name}"
  policy_arn  = "${aws_iam_policy.devbot_lambda_ec2_policy.arn}"
}

resource "aws_iam_role_policy_attachment" "devbot_lambda_sqs" {
  role  = "${aws_iam_role.devbot_lambda_role.name}"
  policy_arn  = "${aws_iam_policy.devbot_lambda_sqs_policy.arn}"
}

resource "aws_lambda_event_source_mapping" "sqs_trig_proc" {
  event_source_arn  = "${aws_sqs_queue.devbot-queue.arn}"
  function_name     = "${aws_lambda_function.proc_new_msg.function_name}"
}
