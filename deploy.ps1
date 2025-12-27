$ErrorActionPreference = "Stop"

$PROJECT_ID = gcloud config get-value project
$PROJECT_NUMBER = gcloud projects describe $PROJECT_ID --format="value(projectNumber)"

$IMAGE = "gcr.io/$PROJECT_ID/makwenta-bot:latest"
$SERVICE = "makwenta-bot-service"
$REGION = "asia-southeast1"

# Write-Host "Cleaning old images..."
# docker rmi -f makwenta-bot 2>$null
# docker rmi -f $IMAGE 2>$null

Write-Host "Building image..."
docker build --no-cache -t makwenta-bot .

Write-Host "Tagging image..."
docker tag makwenta-bot $IMAGE

Write-Host "Pushing image..."
docker push $IMAGE

Write-Host "Deploying to Cloud Run..."
gcloud run deploy $SERVICE `
  --image $IMAGE `
  --region $REGION `
  --platform managed `
  --allow-unauthenticated `
  --set-secrets "TELEGRAM_BOT_TOKEN=telegram-bot-token:latest,OPENAI_API_KEY=openai-api-key:latest,DATABASE_URL=database-url:latest"


Write-Host "Deployment complete!"

