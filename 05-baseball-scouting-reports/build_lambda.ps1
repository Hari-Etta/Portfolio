# Builds build/lambda.zip for AWS Lambda (Python 3.13, x86_64).
# Our code + requests + python-dotenv (Linux wheels). pandas/pyarrow come from the AWS SDK for pandas layer;
# boto3 is built into the Lambda runtime.
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$pkg = Join-Path $root "build\lambda"
$zip = Join-Path $root "build\lambda.zip"

if (Test-Path $pkg) { Remove-Item -Recurse -Force $pkg }
if (Test-Path $zip) { Remove-Item -Force $zip }
New-Item -ItemType Directory -Force (Join-Path $pkg "src\ingest") | Out-Null

pip install "requests==2.34.2" "python-dotenv==1.2.4" `
    --target $pkg `
    --platform manylinux2014_x86_64 --implementation cp --python-version 3.13 `
    --only-binary=:all: --upgrade --quiet

Copy-Item (Join-Path $root "src\__init__.py") (Join-Path $pkg "src\")
foreach ($f in "__init__.py", "s3_utils.py", "mlb_api.py", "daily_handler.py") {
    Copy-Item (Join-Path $root "src\ingest\$f") (Join-Path $pkg "src\ingest\")
}

Compress-Archive -Path (Join-Path $pkg "*") -DestinationPath $zip
"built $zip ($([math]::Round((Get-Item $zip).Length / 1KB)) KB)"
