# Setup AWS Infrastructure

IMPORTANT: The below steps assume you already have an AWS Route 53 Domain or other public domain registered with AWS Route 53 to enable you to register certificates for the ALBs for Keycloak (Public Hosted Zone), UI (Public Hosted Zone) and API (Public Hosted Zone) so you can add CNAME records to AWS Route 53 to route HTTPs traffic from routes on the public domain to the ALBs for Keycloak, UI and API, to enable you to expose them on the public internet. NOTE: Registering a public domain will incurr costs to yourself.

To set up the DNS and Domain for use with the certificates for Keycloak, UI and API in your EKS cluster, follow these steps:

1. **Register a Domain**:
   - If you don't already have a domain, you can register one through AWS Route 53 or any other domain registrar. Note that AWS Route 53 in the AWS test accounts given to you do not allow you to do this, you will need to do this using AWS Route 53 in your own AWS account.

2. **Create a Hosted Zone in Route 53**:
   - In the AWS Management Console (in your own AWS account), go to Route 53 and create a public hosted zone for your domain.
   - This will provide you with a set of name servers (NS records) that you need to configure with your domain registrar.

3. **Request a Certificate in ACM**:
   - Use AWS Certificate Manager (ACM) to request a certificate for your domain.
   - Go to the ACM console, request a public certificate, and enter your domain name (e.g., `yourdomain.com`).
   - Choose DNS validation for easier automation.

4. **Validate the Certificate**:
   - ACM will provide a CNAME record that you need to add to your Route 53 hosted zone to validate the certificate.
   - Go to Route 53, select your hosted zone, and create a new CNAME record with the details provided by ACM.

5. **Create DNS Records for Your Service**:
   - Once the certificate is validated, create an A or CNAME record in Route 53 to point your domain to the load balancer created by the AWS Load Balancer Controller.
  
   - You can find the DNS name of the load balancer by running:
  
     ```bash
     kubectl get ingress my-ingress -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
     ```

   - Use this hostname to create a new record in Route 53:
  
     ```yaml
     apiVersion: route53.amazonaws.com/v1
     kind: RecordSet
     metadata:
       name: my-record
       namespace: default
     spec:
       name: <your-domain>
       type: A
       alias:
         name: <load-balancer-dns-name>
         zoneId: <load-balancer-zone-id>
     ```

## Install AWS and other Tools on your computer

- Install the AWS CLI, follow instructions [here](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- Install kubectl and eksctl, follow instructions [here](https://docs.aws.amazon.com/eks/latest/userguide/install-kubectl.html)
- Install HEML, follow instructions [here](https://helm.sh/docs/intro/install/)

## Create an AWS Profile

Using the AWS credentials for your AWS account and following the instructions [here](https://codeolives.com/2020/02/18/how-to-setup-aws-profile-on-your-computer/) create an AWS profile on your computer.

## Setup Keycloak on an AWS VPC



Setup Keycloak on an AWS account by following the instructions on the URL below. Choose the 2nd method shown on the link to create the keycloak recources in a new VPC on the AWS account.

<https://aws-samples.github.io/keycloak-on-aws/en/implementation-guide/deployment/>

## Setup AWS VPC to host UI and API

Use the AWS Cloud formation script below to setup a VPC with the following elements

- VPC with Internet Gateway
- 2 Public and 2 Private Subnets in two AZs
- AWS Secrets Manager
- AWS ECR Registries for the UI and API
- AWS EKS
- AWS Fargate Profile to run the UI and API EKS deployments
- AWS RDS Postgres instance for the API to store it's data

The AWS Cloud formation script to do this is as below. You can login into the AWS account and run the below cloud formation script to in AWS Cloudformation to create the VPC.

<details>

<summary><b>AWS VPC to host UI and API <i>(Click to Expand)</i></b></summary>

``` yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: CloudFormation template to create a VPC with public and private subnets, EKS cluster, RDS instances

Parameters:
  VpcCIDR:
    Type: String
    Default: 10.1.0.0/16
  PublicSubnetCIDR1:
    Type: String
    Default: 10.1.1.0/24
  PublicSubnetCIDR2:
    Type: String
    Default: 10.1.3.0/24
  PrivateSubnetCIDR1:
    Type: String
    Default: 10.1.2.0/24
  PrivateSubnetCIDR2:
    Type: String
    Default: 10.1.4.0/24
  DBUsername:
    Type: String
    Default: appdbadmin
  DBPassword:
    Type: String
    Default: password
  UIAppSelectorLabelValue:
    Type: String
    Default: codeathon-ui
  APIAppSelectorLabelValue:
    Type: String
    Default: codeathon-api


Resources:
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: !Ref VpcCIDR
      EnableDnsSupport: true
      EnableDnsHostnames: true
      Tags:
        - Key: Name
          Value: !Sub ${AWS::StackName}-vpc

  InternetGateway:
    Type: AWS::EC2::InternetGateway
    Properties:
      Tags:
        - Key: Name
          Value: !Sub ${AWS::StackName}-igw

  AttachGateway:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref VPC
      InternetGatewayId: !Ref InternetGateway

  PublicSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: !Ref PublicSubnetCIDR1
      AvailabilityZone: 
        Fn::Select:
          - 0
          - Fn::GetAZs: !Ref "AWS::Region"
      MapPublicIpOnLaunch: true
      Tags:
        - Key: Name
          Value: !Sub ${AWS::StackName}-public-subnet-1
        - Key: !Sub kubernetes.io/cluster/${AWS::StackName}-eks-cluster
          Value: owned      
        - Key: kubernetes.io/role/elb
          Value: 1

  PublicSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: !Ref PublicSubnetCIDR2
      AvailabilityZone: 
        Fn::Select:
          - 1
          - Fn::GetAZs: !Ref "AWS::Region"
      MapPublicIpOnLaunch: true
      Tags:
        - Key: Name
          Value: !Sub ${AWS::StackName}-public-subnet-2
        - Key: !Sub kubernetes.io/cluster/${AWS::StackName}-eks-cluster
          Value: owned
        - Key: kubernetes.io/role/elb
          Value: 1

  PrivateSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: !Ref PrivateSubnetCIDR1
      AvailabilityZone: 
        Fn::Select:
          - 0
          - Fn::GetAZs: !Ref "AWS::Region"
      Tags:
        - Key: Name
          Value: !Sub ${AWS::StackName}-private-subnet-1
        - Key: !Sub kubernetes.io/cluster/${AWS::StackName}-eks-cluster
          Value: owned
        - Key: kubernetes.io/role/internal-elb
          Value: 1

  PrivateSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: !Ref PrivateSubnetCIDR2
      AvailabilityZone: 
        Fn::Select:
          - 1
          - Fn::GetAZs: !Ref "AWS::Region"
      Tags:
        - Key: Name
          Value: !Sub ${AWS::StackName}-private-subnet-2
        - Key: !Sub kubernetes.io/cluster/${AWS::StackName}-eks-cluster
          Value: owned          
        - Key: kubernetes.io/role/internal-elb
          Value: 1

  RouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: !Sub ${AWS::StackName}-rtb

  PublicRoute:
    Type: AWS::EC2::Route
    Properties:
      RouteTableId: !Ref RouteTable
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref InternetGateway

  SubnetRouteTableAssociation1:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PublicSubnet1
      RouteTableId: !Ref RouteTable

  SubnetRouteTableAssociation2:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PublicSubnet2
      RouteTableId: !Ref RouteTable

  EKSRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: eks.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/AmazonEKSClusterPolicy
        - arn:aws:iam::aws:policy/AmazonEKSServicePolicy

  ECRRepositoryUI:
    Type: "AWS::ECR::Repository"
    Properties:
        RepositoryName: "codeathon2024/ui"
        LifecyclePolicy:
            LifecyclePolicyText: |
                {
                  "rules": [
                    {
                      "rulePriority": 1,
                      "description": "Expire untagged images after 90 days",
                      "selection": {
                        "tagStatus": "untagged",
                        "countType": "sinceImagePushed",
                        "countUnit": "days",
                        "countNumber": 90
                      },
                      "action": {
                        "type": "expire"
                      }
                    }
                  ]
                }

  ECRRepositoryAPI:
    Type: "AWS::ECR::Repository"
    Properties:
        RepositoryName: "codeathon2024/api"
        LifecyclePolicy:
            LifecyclePolicyText: |
                {
                  "rules": [
                    {
                      "rulePriority": 1,
                      "description": "Expire untagged images after 90 days",
                      "selection": {
                        "tagStatus": "untagged",
                        "countType": "sinceImagePushed",
                        "countUnit": "days",
                        "countNumber": 90
                      },
                      "action": {
                        "type": "expire"
                      }
                    }
                  ]
                }

  EKSCluster:
    Type: AWS::EKS::Cluster
    Properties:
      Name: !Sub ${AWS::StackName}-eks-cluster
      ResourcesVpcConfig:
        SubnetIds:
          - !Ref PublicSubnet1
          - !Ref PublicSubnet2
          - !Ref PrivateSubnet1
          - !Ref PrivateSubnet2
      RoleArn: !GetAtt EKSRole.Arn

  RDSInstance:
    Type: AWS::RDS::DBInstance
    Properties:
      DBInstanceClass: db.t3.micro
      Engine: postgres
      MasterUsername: !Ref DBUsername
      MasterUserPassword: !Ref DBPassword
      DBSubnetGroupName: !Ref DBSubnetGroup
      VPCSecurityGroups:
        - !Ref RDSSecurityGroup
      AllocatedStorage: 20


  DBSubnetGroup:
    Type: AWS::RDS::DBSubnetGroup
    Properties:
      DBSubnetGroupDescription: Subnet group for RDS instances
      SubnetIds:
        - !Ref PrivateSubnet1
        - !Ref PrivateSubnet2

  RDSSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Security group for RDS instances
      VpcId: !Ref VPC
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 5432
          ToPort: 5432
          SourceSecurityGroupId: !Ref EKSSecurityGroup

  EKSSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Security group for EKS cluster
      VpcId: !Ref VPC
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 80
          ToPort: 80
          CidrIp: 0.0.0.0/0


  SecretsManager:
    Type: AWS::SecretsManager::Secret
    Properties:
      Name: !Sub ${AWS::StackName}-secrets
      SecretString: !Sub |
        {
          "DBUsername": "${DBUsername}",
          "DBPassword": "${DBPassword}"
        }

  EKSNodeGroupRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: ec2.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy
        - arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy
        - arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly

  EKSNodeGroup:
    Type: AWS::EKS::Nodegroup
    Properties:
      ClusterName: !Ref EKSCluster
      NodeRole: !GetAtt EKSNodeGroupRole.Arn
      Subnets:
        - !Ref PublicSubnet1
        - !Ref PublicSubnet2
        - !Ref PrivateSubnet1
        - !Ref PrivateSubnet2
      ScalingConfig:
        DesiredSize: 2
        MinSize: 1
        MaxSize: 3
      InstanceTypes: ["t3.medium"]
      AmiType: "AL2_x86_64"
      DiskSize: 40
      Labels:
        role: worker
      Tags:
        Name: !Sub ${AWS::StackName}-eks-node-group

  FargatePodExecutionRole:
    Type: AWS::IAM::Role
    Properties: 
      AssumeRolePolicyDocument: 
        Version: '2012-10-17'
        Statement: 
          - Effect: Allow
            Principal: 
              Service: 
                - eks-fargate-pods.amazonaws.com
            Action: 
              - sts:AssumeRole
      ManagedPolicyArns: 
        - arn:aws:iam::aws:policy/AmazonEKSFargatePodExecutionRolePolicy

  FargateProfile:
    Type: AWS::EKS::FargateProfile
    Properties: 
      ClusterName: !Ref EKSCluster
      FargateProfileName: !Sub ${AWS::StackName}-fargate-profile
      PodExecutionRoleArn: !GetAtt FargatePodExecutionRole.Arn
      Subnets: 
        - !Ref PrivateSubnet1
        - !Ref PrivateSubnet2
      Selectors: 
        - Namespace: default
          Labels:
            app: !Ref UIAppSelectorLabelValue
        - Namespace: default
          Labels:
            app: !Ref APIAppSelectorLabelValue
```

</details>

## Setup the AWS EKS Load Balancer controller

Once the above VPCs have been setup on your account. The AWS Load balancer controller will need to be installed.

The AWS EKS load balancer controller will automatically create an ALB when you deploy the EKS deployment for your UI and API on EKS.

To configure your AWS Application Load Balancer (ALB) to point to your EKS deployment, you will need to make use of the AWS Load Balancer Controller for Kubernetes. Here's how you can set this up:

### Add the EKS cluster to your local Kube Config

(Example below modify to suit your own environment)

```` Powershell
aws eks --profile codeathon update-kubeconfig --name Codeathon2024-eks-cluster --region eu-west-2
````

### Add 'profile' environment variable for eksctl

(Example below for windows powershell, used EXPORT for Linux, modify to suit your own environment)

``` Powershell
$env:AWS_PROFILE="codeathon"
```

Then install tha AWS EKS Load Balancer controller using the powershell script like the below.

(Please modify the powershell script parameters to suit your own AWS environment)

``` Powershell
param (
    [string]$AWSProfile = "codeathon",
    [string]$Region = "eu-west-2",
    [string]$ClusterName = "Codeathon2024-eks-cluster",
    [string]$PolicyName = "AWSLoadBalancerControllerIAMPolicy",
    [string]$Namespace = "kube-system",
    [string]$ServiceAccountName = "aws-load-balancer-controller",
    [string]$VpcId = "",
 [string]$PolicyJsonURL = "https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/main/docs/install/iam_policy.json"
)

# Set AWS Profile

$env:AWS_PROFILE = $AWSProfile

# Associate IAM OIDC Provider

eksctl utils associate-iam-oidc-provider --region $Region --cluster $ClusterName --approve

# Download IAM policy JSON
curl -o iam_policy.json $PolicyJsonURL

# Create IAM policy
$policyArn = $(aws iam --profile $AWSProfile create-policy --policy-name $PolicyName --policy-document file://iam_policy.json --output text --query Policy.Arn)

# Create IAM service account
eksctl create iamserviceaccount --cluster $ClusterName --namespace $Namespace --name $ServiceAccountName --attach-policy-arn $policyArn --approve

# Install AWS Load Balancer Controller using Helm
helm install $ServiceAccountName eks/aws-load-balancer-controller -n $Namespace --set clusterName=$ClusterName --set serviceAccount.create=false --set region=$Region --set vpcId=$VpcId --set serviceAccount.name=$ServiceAccountName

```

## Build and Deploy UI to ECR

### Authenticate ECR

Example of the command to authenticate to ECR, adapt to suit your own environment

```Powershell
aws ecr  --profile <aws profile name> get-login-password --region <aws region> | docker login --username AWS --password-stdin <aws account id>.dkr.ecr.<aws region>.amazonaws.com

```

### Build an Image for the UI using Docker and a Docker File

Build an image for your UI using Docker and a Docker file, example Docker fileshown below adapt to suit your own application

```docker
# Dockerfile

# Use an official Node.js runtime as a parent image
FROM node:18 AS builder

# Set the working directory
WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application code
COPY . .


# Build the Next.js application
RUN npm run build

# Use a lightweight web server to serve the built application
FROM node:18-alpine AS runner

WORKDIR /app

# Copy built files from the builder stage
COPY --from=builder /app/.next/ ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/public ./public

# Expose the port the app runs on
EXPOSE 3000

# Run the Next.js application
CMD ["npm", "run", "start"]

```

#### Build and push your Docker image to ECR

Below is an example of the sequence of commands to build a docker image for the UI and push it to ECR

```Powershell
# Build Docker Image

docker build -t codeathon2024/ui:nextjs .

# Tag the image
docker tag codeathon2024/ui:nextjs 330148320511.dkr.ecr.eu-west-2.amazonaws.com/codeathon2024/ui:nextjs

# Push the image to your ECR repository

docker push 330148320511.dkr.ecr.eu-west-2.amazonaws.com/codeathon2024/ui:nextjs

```

#### Create a certificate for the public facing UI

Create and validate, using DNS validation, a certificate for a public domain as per the instructions at the very top.

#### Create an EKS deployment for the UI

Create an EKS deployment for the UI using the ECR image above and deploy it to EKS. Example deployment.yaml show below, adapt to suit your own environment.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: codeathon-ui-deployment
spec:
  replicas: 2
  selector:
    matchLabels:
      app: codeathon-ui
  template:
    metadata:
      labels:
        app: codeathon-ui
    spec:
      containers:
      - name: codeathon-ui-container
        # The ARN of the docker image for the UI uploaded to ECR in the previous step 
        image: 330148320511.dkr.ecr.eu-west-2.amazonaws.com/codeathon2024/ui:nextjs
        ports:
        - containerPort: 3000
      imagePullSecrets:
      - name: aws-ecr-secret
---
apiVersion: v1
kind: Service
metadata:
  name: codeathon-ui-service
spec:
  selector:
    app: codeathon-ui
  ports:
  - protocol: TCP
    port: 80
    targetPort: 3000
  type: NodePort
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: codeathon-ui-ingress
  annotations:   
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS":443}]'
    # The ARN of the certificate created in the previous step
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:eu-west-2:330148320511:certificate/5cf1bfd2-b12c-4364-8e0a-57bb21f46f30
spec:
  ingressClassName: alb
  rules:
       # The domain name for the UI
     - host: team1-codeathon.fitch.group
       http:
         paths:
           - path: /
             pathType: Prefix
             backend:
               service:
                 name: codeathon-ui-service
                 port:
                   number: 80
```

#### Deploy the above image to EKS

Use the command below to deploy the above deployment to EKS

```bash
     kubectl apply -f deployment.yaml
```

#### Deploy the API

Follow a similar set of steps to deploy the API to EKS as done for the UI, note that the API will need to be configured to use the AWS RDS instance in the VPC.

## Hosting the UI on S3

If you don't want to host the UI on EKS as described above you can also host the UI on S3 and create point the AWs Route 53 DNS to the URL of the public S3 bucket. Adapt the instructions below to suit your environment.

- Build Your Next.js Application
First, ensure your Next.js application is ready for production by building it.

- Export the Static Site
Modify your package.json to include the export script:

```json
"scripts": {
  "build": "next build && next export"
}
```

Run the build command to generate static files:

```
npm run build
```

This will create an **out** directory containing your static site.

- Set Up an S3 Bucket
  1. Log in to the AWS Management Console.
  2. Navigate to S3 and click on Create bucket.
  3. Name your bucket the same name as your application.
  4. Enable public access by unchecking “Block all public access” and acknowledging the warning.
  5. Enable static website hosting in the bucket properties. Set the index document to index.html.

- Upload Your Static Files using the AWS Console
  - Go to your S3 bucket.
  - Click on Upload and add the contents of the out directory.
  - Once uploaded, your site should be accessible via the S3 bucket URL.
  - Configure Bucket Policy
  To make your site publicly accessible, add a bucket policy

```json

{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::<Name of S3 Bucket with UI>/*"
    }
  ]
}

```

Access the UI using the S3 bucket URL provided in the static website hosting settings.
